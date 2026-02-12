import sys
import os

# --- PATH FIX: Add project root to python path ---
# This allows us to run this file directly from the terminal
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path: sys.path.append(project_root)
# -------------------------------------------------

import io
import cv2
import numpy as np
from googleapiclient.http import MediaIoBaseDownload
from src.services.drive_manager import DriveManager

class VisionEngine:
    """
    The 'Eye' of AURA.
    Responsibilities:
    1. Download files from Drive into Memory (RAM).
    2. Pre-process images (Grayscale, Threshold) for high-accuracy OCR.
    """
    
    def __init__(self):
        self.drive = DriveManager() # We use the drive manager to get the service

    def download_file_to_memory(self, file_id: str, mime_type: str) -> np.ndarray:
        """
        Downloads a file from Google Drive directly into a NumPy array (OpenCV format).
        Zero-Disk Policy: Data never touches the hard drive.
        """
        try:
            print(f"   [...] Downloading file ID: {file_id}...")
            request = self.drive.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            # Reset buffer pointer to beginning
            file_buffer.seek(0)
            
            # Convert raw bytes to OpenCV Image
            file_bytes = np.asarray(bytearray(file_buffer.read()), dtype=np.uint8)
            
            # Decode image (handles JPG, PNG, WEBP)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
            if img is None:
                raise ValueError("Could not decode image data.")
                
            return img
            
        except Exception as e:
            print(f"[ERROR] Download failed for {file_id}: {e}")
            return None

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Applies Computer Vision filters to make text readable.
        Pipeline: Grayscale -> Gaussian Blur -> Otsu Thresholding.
        """
        if image is None: return None

        # 1. Convert to Grayscale (Text doesn't need color)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 2. Gaussian Blur (Removes noise/grain from bad phone cameras)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 3. Adaptive Thresholding (Binarization)
        # This turns the image into pure Black & White, separating text from background
        processed = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        return processed

# --- Unit Test ---
if __name__ == "__main__":
    print("--- Vision Engine Test (v1.1) ---")
    
    # 1. Initialize
    try:
        vision = VisionEngine()
        dm = DriveManager()
    except Exception as e:
        print(f"[CRITICAL FAIL] Init error: {e}")
        sys.exit(1)
    
    # 2. Get a real file to test
    link = input("Enter Drive Link: ")
    f_id = dm.extract_folder_id(link)
    
    if not f_id:
        print("[FAIL] Invalid Link")
        sys.exit()

    print(f"[INFO] Scanning folder: {f_id}")
    files = dm.list_files(f_id)
    
    if files:
        target = files[0] # Pick the first file
        print(f"[INFO] Target Selected: {target['name']} ({target['mime']})")
        
        # 3. Download
        raw_img = vision.download_file_to_memory(target['id'], target['mime'])
        
        if raw_img is not None:
            print(f"[SUCCESS] Image Loaded into RAM. Shape: {raw_img.shape}")
            
            # 4. Process
            clean_img = vision.preprocess_image(raw_img)
            print("[SUCCESS] Image Pre-processed (Grayscale + Threshold applied).")
            print(f"   - Original Size: {raw_img.size} bytes")
            print(f"   - Processed Type: {clean_img.dtype}")
    else:
        print("[WARN] No files found in this folder to test.")