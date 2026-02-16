import re
import numpy as np
from typing import Dict, Any

try:
    from doctr.io import DocumentFile
    from doctr.models import ocr_predictor
    DOCTR_AVAILABLE = True
except ImportError:
    DOCTR_AVAILABLE = False

class VisionEngine:
    """
    VISION ENGINE v21.0 (THE HAWK EYE)
    Standard: Enterprise docTR
    
    CRITICAL FIXES:
    1. HEADER EXCLUSION: Ignores Top 8% (Kills Battery '56%', Time '12:18').
    2. SIZE PRIORITY: Selects the 'Largest' number visually (Kills tiny metadata).
    3. SYMBOL LOCK: Prioritizes numbers next to '₹'.
    """

    def __init__(self):
        if DOCTR_AVAILABLE:
            # Re-using the model you already downloaded
            self.model = ocr_predictor(det_arch='db_resnet50', reco_arch='crnn_vgg16_bn', pretrained=True)
        else:
            self.model = None

        self.rx_utr_strict = re.compile(r'\b\d{12}\b')
        self.rx_date_trap = re.compile(r'^(25|26|27)(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])')

    def process_file(self, file_stream, filename: str) -> Dict[str, Any]:
        if not self.model:
            return {'status': 'FAILED', 'reason': 'Library Missing', 'amount': 0.0, 'utr': None}

        try:
            file_bytes = file_stream.read()
            doc = DocumentFile.from_images(file_bytes)
            result = self.model(doc)
            return self._parse_semantic_layout(result)
        except Exception as e:
            return {'status': 'FAILED', 'reason': f"Error: {str(e)}", 'amount': 0.0, 'utr': None}

    def _parse_semantic_layout(self, result) -> Dict[str, Any]:
        page = result.pages[0]
        h_page, w_page = page.dimensions
        
        candidates_amt = []
        candidates_utr = []

        for block in page.blocks:
            for line in block.lines:
                text = " ".join([word.value for word in line.words])
                text_clean = text.replace(' ', '').upper()
                
                # Geometry: ((x1, y1), (x2, y2))
                # y_center is relative (0.0 = Top, 1.0 = Bottom)
                y1 = line.geometry[0][1]
                y2 = line.geometry[1][1]
                y_center = (y1 + y2) / 2
                
                # Calculate Font Height (Relative to page)
                font_height = y2 - y1

                # --- 1. AMOUNT LOGIC ---
                # RULE A: Header Exclusion (Ignore Top 8% - Battery/Time)
                # RULE B: Amount Zone (Must be in Top 50%)
                if 0.08 < y_center < 0.50:
                    self._analyze_amount(text, font_height, candidates_amt)

                # --- 2. UTR LOGIC ---
                # Check for Labels "UTR", "REF", "TXN"
                if any(x in text_clean for x in ["UTR", "REF", "TXN", "ID"]):
                     digits = self.rx_utr_strict.findall(text_clean)
                     for d in digits:
                         if not self._is_date_trap(d):
                             candidates_utr.append({'val': d, 'score': 1000})
                else:
                    # Raw 12-digit search
                    digits = self.rx_utr_strict.findall(text_clean)
                    for d in digits:
                        if not self._is_date_trap(d):
                            candidates_utr.append({'val': d, 'score': 50})

        return self._synthesize(candidates_amt, candidates_utr)

    def _analyze_amount(self, text, height, candidates):
        """
        Parses line for money. Scores based on Size + Symbol.
        """
        # 1. Hard Filter: Reject Timestamps/Dates
        if any(x in text for x in [':', '/', '-']): return
        if "202" in text and "₹" not in text: return
        
        # 2. Extract Numbers
        # Remove symbols to parse value
        val_text = text.replace('₹', '').replace('Rs', '').replace(',', '').strip()
        try:
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", val_text)
            for n in nums:
                val = float(n)
                # Sanity Range
                if 1.0 <= val <= 200000.0:
                    # --- SCORING ALGORITHM ---
                    # Base Score
                    score = 10
                    
                    # Bonus 1: Currency Symbol (Huge Confidence)
                    if '₹' in text or 'Rs' in text: 
                        score += 500
                    
                    # Bonus 2: Font Size (The "Hawk Eye")
                    # Amounts are usually the biggest text. 
                    # We multiply height by 1000 to make it significant.
                    score += (height * 1000)
                    
                    candidates.append({'val': val, 'score': score, 'text': text})
        except: pass

    def _is_date_trap(self, digit_str):
        if digit_str.startswith('0000'): return True
        return bool(self.rx_date_trap.match(digit_str))

    def _synthesize(self, cands_amt, cands_utr) -> Dict[str, Any]:
        # Sort by Score (Highest First)
        final_amt = 0.0
        if cands_amt:
            cands_amt.sort(key=lambda x: x['score'], reverse=True)
            final_amt = cands_amt[0]['val']
            
        final_utr = None
        if cands_utr:
            cands_utr.sort(key=lambda x: x['score'], reverse=True)
            final_utr = cands_utr[0]['val']

        # Logic Matrix
        if final_amt > 0 and final_utr:
            return {'status': 'SUCCESS', 'amount': final_amt, 'utr': final_utr}
        elif final_amt > 0:
            return {'status': 'MANUAL_REVIEW', 'amount': final_amt, 'utr': None, 'reason': 'UTR missing'}
        elif final_utr:
            return {'status': 'MANUAL_REVIEW', 'amount': 0.0, 'utr': final_utr, 'reason': 'Amount unclear'}
        else:
            return {'status': 'FAILED', 'amount': 0.0, 'utr': None, 'reason': 'No Readable Data'}