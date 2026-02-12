import sys
import os
import re
import io
import cv2
import pytesseract
import numpy as np
from typing import Dict, Any, Optional
from googleapiclient.http import MediaIoBaseDownload

# PATH FIX
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path: sys.path.append(project_root)

from src.services.drive_manager import DriveManager

class VisionEngine:
    PATTERNS = {
        'upi_labeled': r'(?i)(?:UPI\s*Ref\.?\s*No|UTR|Transaction\s*ID|Txn\s*ID|Ref\s*No|Reference\s*ID|Bank\s*Ref|Ref\s*Number)[\s:\-\.]*([A-Z0-9]+)',
        'upi_standalone': r'\b\d{12,25}\b',
        'amount_strict': r'(?:₹|Rs\.?|INR)\s*[\.\-]?\s*([\d,]+\.?\d{0,2})',
        # Removed 'T' from fuzzy to prevent Transaction ID matches
        'amount_fuzzy': r'(?:<|\?|t|R|\|)\s*([\d,]+\.?\d{0,2})\b',
        'date_text': r'(?i)(?:on\s+)?(\d{1,2})[\s\-\/]+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\-\/,]+(\d{4})',
    }

    def __init__(self):
        self.drive = DriveManager()
        if os.path.exists('/opt/homebrew/bin/tesseract'):
            pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

    def download_file_to_memory(self, file_id: str) -> Optional[np.ndarray]:
        try:
            print(f"   [...] Downloading file ID: {file_id}...")
            request = self.drive.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            done = False
            while done is False: status, done = downloader.next_chunk()
            file_buffer.seek(0)
            file_bytes = np.asarray(bytearray(file_buffer.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            print(f"[ERROR] Download failed: {e}")
            return None

    def preprocess_image(self, image: np.ndarray) -> Dict[str, np.ndarray]:
        if image is None: return {}
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        scale_percent = 200 
        width = int(gray.shape[1] * scale_percent / 100)
        height = int(gray.shape[0] * scale_percent / 100)
        upscaled = cv2.resize(gray, (width, height), interpolation = cv2.INTER_AREA)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        inverted = cv2.bitwise_not(binary)
        return {'original': image, 'upscaled': upscaled, 'binary': binary, 'inverted': inverted}

    def run_ocr(self, processed_images: Dict[str, np.ndarray]) -> str:
        full_text = ""
        cfg = r'--oem 3 --psm 6'
        if 'upscaled' in processed_images:
            full_text += pytesseract.image_to_string(processed_images['upscaled'], lang='eng', config=cfg) + "\n"
        if 'inverted' in processed_images:
            full_text += pytesseract.image_to_string(processed_images['inverted'], lang='eng', config=cfg) + "\n"
        return full_text

    def validate_amount(self, val: float) -> bool:
        """GLOBAL SAFETY CHECK: Rejects improbable donation amounts."""
        # 1. Must be positive
        # 2. Must be <= 2,00,000 (2 Lakhs)
        # 3. Must not look like a year (2025, 2026)
        if val <= 0: return False
        if val > 200000: return False 
        if val in [2024, 2025, 2026, 2027]: return False
        return True

    def extract_financials(self, text: str) -> Dict[str, Any]:
        data = { 'amount': 0.0, 'utr': None, 'timestamp': None, 'extracted_text': text }
        
        # --- 1. SANITIZATION (The Nuclear Option) ---
        # Remove "Transaction ID T..." patterns BEFORE processing money
        # matches 'T' followed by 8+ digits
        clean_text = re.sub(r'T\d{8,}', ' ', text)

        # --- 2. UTR EXTRACTION ---
        utr_match = re.search(self.PATTERNS['upi_labeled'], text) # Use original text for UTR
        if utr_match:
            raw_id = utr_match.group(1)
            data['utr'] = re.sub(r'[^A-Za-z0-9]', '', raw_id)
        else:
            all_long_digits = re.findall(self.PATTERNS['upi_standalone'], text)
            if all_long_digits: data['utr'] = all_long_digits[0]

        # --- 3. AMOUNT EXTRACTION (Using Clean Text + Validation) ---
        found_amount = False

        # Priority 1: Strict (₹500)
        strict_matches = re.findall(self.PATTERNS['amount_strict'], clean_text)
        clean_strict = []
        for a in strict_matches:
            try:
                val = float(a.replace(',', ''))
                if self.validate_amount(val): clean_strict.append(val)
            except: pass
        
        if clean_strict:
            data['amount'] = max(clean_strict)
            found_amount = True

        # Priority 2: Fuzzy (<8)
        if not found_amount:
            fuzzy_matches = re.findall(self.PATTERNS['amount_fuzzy'], clean_text)
            clean_fuzzy = []
            for a in fuzzy_matches:
                try:
                    val = float(a.replace(',', ''))
                    if self.validate_amount(val): clean_fuzzy.append(val)
                except: pass
            
            if clean_fuzzy:
                data['amount'] = max(clean_fuzzy)
                found_amount = True

        # Priority 3: Fallback (Generic)
        if not found_amount:
            generic_matches = re.findall(r'\b(\d{1,6}(?:,\d{3})*(?:\.\d{2})?)\b', clean_text)
            clean_generic = []
            for a in generic_matches:
                try:
                    val = float(a.replace(',', ''))
                    if self.validate_amount(val): clean_generic.append(val)
                except: pass
            
            if clean_generic:
                data['amount'] = max(clean_generic)

        # --- 4. DATE ---
        date_match = re.search(self.PATTERNS['date_text'], text)
        if date_match:
            groups = date_match.groups()
            day, month, year = groups[-3], groups[-2], groups[-1]
            data['timestamp'] = f"{day} {month} {year}"
        
        # Validation Status
        if data['utr'] and data['amount'] > 0:
            data['status'] = 'SUCCESS'
        elif data['amount'] > 0:
            data['status'] = 'MANUAL_REVIEW'
        elif data['utr']:
            data['status'] = 'PARTIAL_FAIL'
        else:
            data['status'] = 'FAILED'

        return data

    def analyze_file(self, file_id: str) -> Dict[str, Any]:
        img = self.download_file_to_memory(file_id)
        if img is None: return {'status': 'FAILED', 'reason': 'Download Error'}
        versions = self.preprocess_image(img)
        raw_text = self.run_ocr(versions)
        return self.extract_financials(raw_text)