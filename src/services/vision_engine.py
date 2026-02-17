import re
from typing import Dict, Any, List

try:
    from doctr.io import DocumentFile
    from doctr.models import ocr_predictor
    DOCTR_AVAILABLE = True
except ImportError:
    DOCTR_AVAILABLE = False

class VisionEngine:
    """
    VISION ENGINE v24.0 (SEMANTIC GUARDIAN)
    Fixes:
    1. 'Year as Amount' Bug (Ignores 2026, 2025 in date lines)
    2. 'Ghost 3' Bug (Cleans '3 31.00' to '31.00')
    3. Strict Date/Time filtering for Amount Logic
    """
    def __init__(self, debug_mode=False):
        self.debug = debug_mode
        if DOCTR_AVAILABLE:
            self.model = ocr_predictor(det_arch='db_resnet50', reco_arch='crnn_vgg16_bn', pretrained=True)
        else:
            self.model = None

        self.rx_utr_strict = re.compile(r'\b\d{12}\b') 
        self.rx_date_trap = re.compile(r'(20[2-3]\d)|(19\d{2})')
        
        # New: Explicit months to kill date lines
        self.rx_months = re.compile(r'\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\b', re.IGNORECASE)
        self.rx_time = re.compile(r'\d{1,2}:\d{2}') # Matches 19:22

    def process_file(self, file_stream, filename: str) -> Dict[str, Any]:
        if not self.model:
            return {'status': 'FAILED', 'reason': 'docTR Lib Missing', 'amount': 0.0, 'utr': None}
        
        try:
            file_bytes = file_stream.read()
            doc = DocumentFile.from_images(file_bytes)
            result = self.model(doc)
            lines = self._flatten_to_lines(result)
            
            if self.debug:
                print(f"\n--- DEBUG: RAW LINES FOR {filename} ---")
                for l in lines:
                    print(f"Y: {l['y_center']:.3f} | Text: {l['text']}")
                print("---------------------------------------\n")

            amount = self._isolate_primary_amount(lines)
            utr = self._isolate_utr(lines)

            status = 'SUCCESS' if (amount > 0 and utr) else 'FAILED'
            
            return {
                'status': status,
                'reason': "Low Confidence" if status == 'FAILED' else None, 
                'amount': amount, 
                'utr': utr
            }

        except Exception as e:
            return {'status': 'FAILED', 'reason': f"Crash: {str(e)}", 'amount': 0.0, 'utr': None}

    def _flatten_to_lines(self, result) -> List[Dict]:
        lines_extracted = []
        page = result.pages[0]
        for block in page.blocks:
            for line in block.lines:
                text = " ".join([word.value for word in line.words])
                y1 = line.geometry[0][1]
                y2 = line.geometry[1][1]
                lines_extracted.append({
                    'text': text,
                    'clean_text': text.upper().replace(' ', ''),
                    'y_center': (y1 + y2) / 2,
                    'height': y2 - y1
                })
        return lines_extracted

    def _isolate_primary_amount(self, lines: List[Dict]) -> float:
        candidates = []
        y_paid_to = -1.0
        y_debited = -1.0
        
        # 1. Locate Anchors
        for line in lines:
            t = line['clean_text']
            if any(x in t for x in ["PAIDTO", "TRANSFER", "SUCCESSFUL", "SENTTO"]):
                if y_paid_to == -1: y_paid_to = line['y_center']
            if any(x in t for x in ["DEBITED", "REFUND"]):
                y_debited = line['y_center']

        # 2. Score Candidates
        for line in lines:
            text = line['text']
            y = line['y_center']
            h = line['height']

            # RULE A: Decapitate Status Bar (Battery/Time at very top)
            if y < 0.10 and h < 0.03: continue 

            # RULE B: The "Date Killer" (CRITICAL FIX)
            # If line has "Jan", "Feb" or looks like time "19:22", IT IS NOT MONEY.
            if self.rx_months.search(text) or self.rx_time.search(text):
                continue
            
            # RULE C: Ghost Cleaning (Fixing "3 31.00")
            # If text starts with a single digit + space + number (e.g. "3 31.00"), 
            # assume the first digit is a misread symbol.
            clean_text = text.replace('₹', '').replace('Rs', '').replace(',', '').strip()
            
            # Regex for "Digit Space Number" (e.g., "3 31.00")
            ghost_match = re.match(r'^(\d)\s+(\d+\.?\d*)', clean_text)
            if ghost_match:
                # If the first digit is small (likely misread symbol), take the second part
                if len(ghost_match.group(1)) == 1:
                    clean_text = ghost_match.group(2) # Becomes "31.00"

            # Parse numbers
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", clean_text)
            
            for n in nums:
                try:
                    val = float(n)
                    if 1.0 <= val <= 200000.0:
                        score = 0
                        
                        # --- SCORING ---
                        # 1. Height (Size matters)
                        score += (h * 1000)
                        
                        # 2. Anchor Bonus
                        if y_paid_to != -1 and y_paid_to < y < (y_paid_to + 0.25): score += 500
                        if y_debited != -1 and (y_debited - 0.02) < y < (y_debited + 0.15): score -= 1000
                        
                        # 3. Currency Symbol Bonus
                        if '₹' in text or 'Rs' in text: score += 100
                        
                        # 4. Tie-Breaker (Prefer larger values, but only slightly)
                        score += (val * 0.0001)

                        candidates.append({'val': val, 'score': score})
                except: continue

        if not candidates: return 0.0
        
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        if self.debug and candidates:
            print(f"Winning Amount: {candidates[0]}")
            
        return candidates[0]['val']

    def _isolate_utr(self, lines: List[Dict]) -> str:
        candidates = []
        for line in lines:
            clean = line['clean_text']
            matches = self.rx_utr_strict.findall(clean)
            
            for m in matches:
                score = 0
                
                # UTR Logic: 12 digits is KING.
                # If exact 12 digits, we ignore the date trap.
                if len(m) != 12 and self.rx_date_trap.search(clean): 
                    score -= 500
                
                if any(x in clean for x in ["UTR", "REF", "TXN", "ID", "NO"]): score += 100
                
                candidates.append({'val': m, 'score': score})

        if not candidates: return None
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        best = candidates[0]
        if best['score'] < -50: return None
        return best['val']