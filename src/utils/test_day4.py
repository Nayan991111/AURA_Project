import sys
import os
import time

# --- PATH FIX ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.vision_engine import VisionEngine
from src.services.drive_service import DriveService

def test_ocr_pipeline():
    print("--- [DAY 12] VISION ENGINE v15.0 DIAGNOSTICS ---")
    
    # 1. Initialize
    try:
        engine = VisionEngine()
        print("[OK] VisionEngine (The Guillotine) Loaded")
        ds = DriveService()
        print("[OK] DriveService Connected")
    except Exception as e:
        print(f"[FAIL] Init Error: {e}")
        return

    # 2. Input
    print("\n--- INPUT REQUIRED ---")
    raw_input = input("Paste Google Drive Link/ID: ").strip()
    if not raw_input: return

    # 3. Resolve Target
    target_id = raw_input
    if "drive.google.com" in raw_input:
        try:
            target_id = ds.extract_folder_id(raw_input)
        except:
            pass
            
    print(f"[INFO] Target ID: {target_id}")

    # 4. Download & Analyze
    try:
        # Check if it's a folder or file
        try:
            files = ds.list_files_recursive(target_id)
            if files:
                print(f"[INFO] Target is a FOLDER. Testing first file: {files[0]['name']}")
                target_id = files[0]['id']
                filename = files[0]['name']
            else:
                filename = "Direct_Test.jpg"
        except:
            filename = "Direct_Test.jpg"

        print(f"[...] Downloading {filename}...")
        file_stream = ds.download_file_to_memory(target_id)
        
        print(f"[...] Processing with v15.0 Engine...")
        start = time.time()
        result = engine.process_file(file_stream, filename)
        duration = time.time() - start

        # 5. Report
        print("\n" + "="*40)
        print(f"   VISION REPORT v15.0")
        print("="*40)
        print(f"⏱️  Time: {duration:.3f}s")
        print(f"📊 Status: {result['status']}")
        
        if result['status'] == 'SUCCESS':
             print(f"✅ Amount: ₹{result['amount']}")
             print(f"🔍 UTR:    {result['utr']}")
        else:
             print(f"❌ Reason: {result.get('reason')}")
             print(f"⚠️ Raw Amt: {result.get('amount')}")
             print(f"⚠️ Raw UTR: {result.get('utr')}")
        print("="*40)

    except Exception as e:
        print(f"[CRITICAL FAIL] {e}")

if __name__ == "__main__":
    test_ocr_pipeline()
