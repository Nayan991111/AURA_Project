import cv2
import pytesseract
import numpy as np
import re
from typing import Dict, Any
from pytesseract import Output

class VisionEngine:
    """
    VISION ENGINE v14.0 (The Eraser)
    - DOUBLE-PASS OCR:
      1. Find coordinates of dates/years/noise.
      2. PAINT OVER them with white pixels.
      3. Read the clean image to get pure amounts.
    """

    def __init__(self):
        # M4 Silicon Path
        self.tesseract_cmd = '/opt/homebrew/bin/tesseract'
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def process_file(self, file_stream, filename: str) -> Dict[str, Any]:
        try:
            # 1. Load Image
            file_bytes = np.asarray(bytearray(file_stream.read()), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if image is None: return {'status': 'FAILED', 'reason': 'Corrupt Image'}

            # 2. Preprocess (Standard)
            # Check Dark Mode
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            if np.mean(gray) < 127: gray = cv2.bitwise_not(gray) # Invert if dark
            
            # Upscale
            scale = 2.0
            processed = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            processed = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

            # 3. PASS 1: THE SCOUT (Find Noise)
            d = pytesseract.image_to_data(processed, output_type=Output.DICT, config=r'--oem 3 --psm 6')
            n_boxes = len(d['text'])
            
            # Create a copy to paint on
            clean_image = processed.copy()
            
            # List of noise patterns to ERASE
            noise_patterns = [
                r'202[4-9]', # Years
                r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', # Months
                r'(PM|AM)', # Time
                r'Paid',
                r'seconds',
                r'3290', # Bank Account
                r'Success'
            ]
            
            for i in range(n_boxes):
                text = d['text'][i].strip()
                if not text: continue
                
                # Check if this word is noise
                is_noise = False
                for pattern in noise_patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        is_noise = True
                        break
                
                # If it's noise, PAINT IT WHITE
                if is_noise:
                    (x, y, w, h) = (d['left'][i], d['top'][i], d['width'][i], d['height'][i])
                    # Draw a white rectangle over it
                    cv2.rectangle(clean_image, (x, y), (x + w, y + h), (255, 255, 255), -1)

            # 4. PASS 2: THE READER (Scan Clean Image)
            # Now we scan the image where dates are literally deleted
            clean_text = pytesseract.image_to_string(clean_image, lang='eng', config=r'--oem 3 --psm 6')
            
            # 5. Extract Data
            return self._extract_data(clean_text, d) # Pass original data for UTR search

        except Exception as e:
            return {'status': 'FAILED', 'reason': str(e)}

    def _extract_data(self, clean_text: str, original_data: Dict) -> Dict[str, Any]:
        data = {'amount': 0.0, 'utr': None, 'status': 'FAILED', 'reason': 'No Data'}
        
        # --- PHASE 1: AMOUNT HUNT (On Clean Text) ---
        # Cleanup
        text = clean_text.replace('l', '1').replace('O', '0').replace('o', '0')
        text = re.sub(r'(?i)(z|Z|t|T|\?|7|f)\s*(\d)', r'₹\2', text)
        
        candidates = []
        
        # 1. Look for Symbol Matches (Strongest)
        matches = re.findall(r'(?:₹|Rs|INR)\s*([\d,]+\.?\d{0,2})', text)
        for m in matches:
            try:
                val = float(m.replace(',', ''))
                if 1.0 <= val <= 200000.0: candidates.append(val)
            except: pass
            
        # 2. Look for Naked Numbers
        if not candidates:
            nums = re.findall(r'\b(\d{1,6}(?:,\d{3})*(?:\.\d{2})?)\b', text)
            for n in nums:
                try:
                    val = float(n.replace(',', ''))
                    if 1.0 <= val <= 200000.0: candidates.append(val)
                except: pass

        if candidates:
            data['amount'] = max(candidates)

        # --- PHASE 2: UTR HUNT (Using Original Data) ---
        # We use the original scan because we might have accidentally erased part of a UTR if it looked like a date
        full_text = " ".join(original_data['text'])
        
        # Clean for regex
        blob = re.sub(r'[^a-zA-Z0-9]', '', full_text)
        
        # Find 12 digits
        utrs = re.findall(r'(\d{12})', blob)
        for u in utrs:
            if not u.startswith('0000') and not u.startswith('2026'):
                data['utr'] = u
                break
        
        # Fallback for PhonePe (T...)
        if not data['utr']:
            txn = re.search(r'T(\d{20,})', blob)
            if txn: data['utr'] = txn.group(1)[-12:]

        # --- FINAL STATUS ---
        if data['utr'] and data['amount'] > 0:
            data['status'] = 'SUCCESS'
            data['reason'] = ''
        elif data['amount'] > 0:
            data['status'] = 'MANUAL_REVIEW'
            data['reason'] = f"Found ₹{data['amount']} but UTR missing"
        elif data['utr']:
            data['status'] = 'PARTIAL_FAIL'
            data['reason'] = f"Found UTR {data['utr']} but Amount unclear"
        else:
            data['status'] = 'FAILED'
            data['reason'] = "Image quality low"

        return data