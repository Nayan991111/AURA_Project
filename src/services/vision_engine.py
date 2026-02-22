import re
from typing import Dict, Any, List

try:
    from doctr.io import DocumentFile
    from doctr.models import ocr_predictor
    DOCTR_AVAILABLE = True
except Exception:
    DOCTR_AVAILABLE = False


class VisionEngine:
    """
    VISION ENGINE v24.1 (SEMANTIC GUARDIAN)
    - Improved amount candidate filtering and scoring
    - Explicit rupee handling
    - Metadata/date/time line rejection
    - Better ghost-number cleaning
    """

    def __init__(self, debug_mode: bool = False):
        self.debug = debug_mode
        if DOCTR_AVAILABLE:
            self.model = ocr_predictor(det_arch='db_resnet50', reco_arch='crnn_vgg16_bn', pretrained=True)
        else:
            self.model = None

        # Patterns
        self.rx_utr_strict = re.compile(r'\b\d{12}\b')
        self.rx_date_trap = re.compile(r'\b(19\d{2}|20\d{2})\b')
        self.rx_months = re.compile(r'\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|JANUARY|FEBRUARY)\b', re.IGNORECASE)
        self.rx_time = re.compile(r'\b\d{1,2}:\d{2}\b')
        self.rx_metadata_tokens = re.compile(
            r'\b(BANK|DEBITED|DEBIT|SENTWITH|SENTTO|SENT|RECEIVED|TRANSACTION|TRANSACTIONID|TXN|REF|UPI|VIEW|DETAIL|POWERED|COMMUNITY|CHATS|SETTINGS|TRANSFER|TRANSFERDETAILS|TRANFER)\b',
            re.IGNORECASE
        )
        self.rx_rupee = re.compile(r'(₹|Rs\.?|INR)', re.IGNORECASE)
        # flexible number finder (captures comma grouped & decimal)
        self.rx_number = re.compile(r"[-+]?\d{1,3}(?:[,\d]{0,}\d)?(?:\.\d+)?|\d+\.\d+|\d+")

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
                    print(f"Y: {l['y_center']:.3f} | H: {l['height']:.3f} | Text: {l['text']}")
                print("---------------------------------------\n")

            amount = self._isolate_primary_amount(lines)
            utr = self._isolate_utr(lines)

            status = 'SUCCESS' if (amount > 0 and utr) else 'FAILED'

            return {
                'status': status,
                'reason': None if status == 'SUCCESS' else "Low Confidence",
                'amount': amount,
                'utr': utr
            }

        except Exception as e:
            return {'status': 'FAILED', 'reason': f"Crash: {str(e)}", 'amount': 0.0, 'utr': None}

    def _flatten_to_lines(self, result) -> List[Dict]:
        lines_extracted: List[Dict] = []
        # defensive: handle pages if multiple; primarily using first page
        page = result.pages[0]
        for block in page.blocks:
            for line in block.lines:
                text = " ".join([word.value for word in line.words]).strip()
                # geometry may be absolute or relative; keep defensive defaults
                try:
                    y1 = float(line.geometry[0][1])
                    y2 = float(line.geometry[1][1])
                except Exception:
                    y1 = 0.0
                    y2 = 0.0
                height = abs(y2 - y1)
                lines_extracted.append({
                    'text': text,
                    'clean_text': re.sub(r'\s+', '', text.upper()),
                    'y_center': (y1 + y2) / 2 if (y1 is not None and y2 is not None) else 0.0,
                    'height': height
                })
        return lines_extracted

    def _line_looks_like_metadata(self, text: str) -> bool:
        if self.rx_metadata_tokens.search(text):
            return True
        if re.search(r'\bvia\b', text, re.IGNORECASE):
            return True
        if re.search(r'\bUPI\b', text, re.IGNORECASE):
            return True
        if re.search(r'\bBANK\b', text, re.IGNORECASE):
            return True
        return False

    def _clean_number_text(self, s: str) -> str:
        # Remove currency words and stray characters
        s = s.replace('₹', '').replace('Rs', '').replace('INR', '').replace('rupees', '')
        s = s.strip()
        # Collapse common OCR ghost patterns like '3 31.00' -> '31.00'
        ghost_match = re.match(r'^(\d)\s+(\d+[\d,]*\.?\d*)$', s)
        if ghost_match:
            s = ghost_match.group(2)
        # Remove spaces and commas inside numeric tokens
        s = re.sub(r'[\s,]+', '', s)
        # Strip anything except digits and dot
        s = re.sub(r'[^\d\.]', '', s)
        return s

    def _isolate_primary_amount(self, lines: List[Dict]) -> float:
        candidates = []
        y_paid_to = -1.0
        y_debited = -1.0

        # locate anchors
        for line in lines:
            t = line['clean_text']
            if any(x in t for x in ["PAIDTO", "PAYMENT", "PAYMENTSUCCESSFUL", "PAYMENTSUCCESS", "PAYMENTSHOULD", "SENTTO", "SENTWITH", "SENT", "PAID", "COMPLETED"]):
                if y_paid_to == -1:
                    y_paid_to = line['y_center']
            if any(x in t for x in ["DEBITED", "DEBIT", "REFUND"]):
                y_debited = line['y_center']

        for line in lines:
            raw_text = line['text']
            clean_text = line['clean_text']
            y = line['y_center']
            h = line['height']

            # top status bar noise
            if y < 0.06 and h < 0.03:
                continue

            # if line clearly metadata and no explicit rupee sign, skip
            if self._line_looks_like_metadata(raw_text) and not self.rx_rupee.search(raw_text):
                continue

            # skip if contains month or time (date/time)
            if self.rx_months.search(raw_text) or self.rx_time.search(raw_text):
                # allow if explicit rupee and large font
                if not self.rx_rupee.search(raw_text) or h < 0.02:
                    continue

            # prefer explicit rupee matches
            rupee_match = re.search(r'(₹\s*[\d,]+(?:\.\d+)?)', raw_text)
            if rupee_match:
                rupee_val = rupee_match.group(1)
                rupee_val = re.sub(r'[₹\s,]', '', rupee_val)
                try:
                    v = float(rupee_val)
                    if 0.5 <= v <= 2000000:
                        score = 200 + (h * 1000)
                        if y_paid_to != -1 and y_paid_to < y < (y_paid_to + 0.30):
                            score += 500
                        if y_debited != -1 and (y_debited - 0.02) < y < (y_debited + 0.15):
                            score -= 1000
                        candidates.append({'val': v, 'score': score, 'line': raw_text})
                        if self.debug:
                            print(f"Rupee explicit parse -> {v} (line: {raw_text})")
                        continue
                except Exception:
                    pass

            # otherwise extract numeric tokens
            raw_nums = self.rx_number.findall(raw_text)
            for raw_n in raw_nums:
                norm = self._clean_number_text(raw_n)
                if not norm:
                    continue
                try:
                    val = float(norm)
                except Exception:
                    continue

                if not (0.5 <= val <= 2000000):
                    continue

                line_penalty = 0
                if self.rx_metadata_tokens.search(raw_text):
                    line_penalty -= 250
                if re.search(r'\b(via|xxxx|xxxxxx|x{3,})\b', raw_text, re.IGNORECASE):
                    line_penalty -= 200
                if len(norm) <= 4 and not self.rx_rupee.search(raw_text):
                    line_penalty -= 300
                if self.rx_date_trap.search(raw_text):
                    line_penalty -= 400

                score = (h * 1000) + (val * 0.0001) + line_penalty

                if y_paid_to != -1 and y_paid_to < y < (y_paid_to + 0.30):
                    score += 500
                if y_debited != -1 and (y_debited - 0.02) < y < (y_debited + 0.15):
                    score -= 1000
                if self.rx_rupee.search(raw_text):
                    score += 120

                candidates.append({'val': val, 'score': score, 'line': raw_text})

        if not candidates:
            if self.debug:
                print("No amount candidates found.")
            return 0.0

        candidates.sort(key=lambda x: x['score'], reverse=True)

        if self.debug:
            print("Top amount candidates (top 5):")
            for c in candidates[:5]:
                print(f"  val: {c['val']}  score: {c['score']:.2f}  line: {c.get('line')}")

        top = candidates[0]
        # prefer rupee-containing candidate if very close in score
        if not self.rx_rupee.search(str(top.get('line', ''))):
            for c in candidates:
                if self.rx_rupee.search(str(c.get('line', ''))):
                    if c['score'] >= top['score'] - 50:
                        top = c
                        break

        return float(top['val'])

    def _isolate_utr(self, lines: List[Dict]) -> str:
        candidates = []
        for line in lines:
            clean = line['clean_text']
            matches = self.rx_utr_strict.findall(clean)
            for m in matches:
                score = 0
                if any(x in clean for x in ["UTR", "REF", "TXN", "TRANSACTIONID", "TRANSACTION", "ID", "NO"]):
                    score += 250
                if self.rx_date_trap.search(clean) and len(m) != 12:
                    score -= 500
                candidates.append({'val': m, 'score': score, 'line': line['text']})

        if not candidates:
            return None

        candidates.sort(key=lambda x: x['score'], reverse=True)
        best = candidates[0]
        if self.debug:
            print("UTR candidates:", candidates[:4])
        if best['score'] < -50:
            return None
        return best['val']