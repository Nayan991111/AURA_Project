import sys
import os
import time

# --- PATH FIX (CRITICAL FOR M4) ---
# This ensures Python can find 'src' regardless of where you run the script from
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# -----------------------------

from src.services.vision_engine import VisionEngine

def test_ocr_pipeline():
    print("--- [DAY 12] VISION ENGINE v15.0 DIAGNOSTICS ---")
    print("[INIT] Booting 'The Guillotine' Engine on Apple Silicon...")
    
    # 1. Initialize
    try:
        engine = VisionEngine()
        print("[OK] VisionEngine Loaded Successfully")
    except Exception as e:
        print(f"[FAIL] Could not init VisionEngine: {e}")
        return

    # 2. Input
    print("\n--- INPUT REQUIRED ---")
    raw_input = input("Paste a Google Drive Link (Folder or File) or ID: ").strip()
    
    if not raw_input:
        print("[SKIP] No input provided.")
        return

    # 3. Smart ID Resolution (Using internal drive service if available, else raw)
    target_id = raw_input
    if "drive.google.com" in raw_input:
        # Simple extraction for the test script
        if "folders/" in raw_input:
            target_id = raw_input.split("folders/")[1].split("?")[0]
        elif "id=" in raw_input:
            target_id = raw_input.split("id=")[1].split("&")[0]
        print(f"[INFO] Extracted ID: {target_id}")

    # 4. Run Analysis
    print(f"\n[...] Downloading & Analyzing ID: {target_id}...")
    
    # We need to simulate the Drive Download + Memory Stream for the engine
    from src.services.drive_service import DriveService
    ds = DriveService()
    
    try:
        # Check if it is a folder (if so, pick the first image)
        try:
            # Try to see if it's a folder
            files = ds.list_files_recursive(target_id)
            if files:
                print(f"[INFO] Target is a FOLDER with {len(files)} files.")
                target_file = files[0]
                print(f"[INFO] Testing first file: {target_file['name']}")
                file_stream = ds.download_file_to_memory(target_file['id'])
                filename = target_file['name']
            else:
                # Target is likely a file itself
                print("[INFO] Target appears to be a direct file.")
                file_stream = ds.download_file_to_memory(target_id)
                filename = "Direct_Test_File.jpg"
        except:
            # Fallback: Treat as direct file
            file_stream = ds.download_file_to_memory(target_id)
            filename = "Direct_Test_File.jpg"

        # EXECUTE v15.0 ENGINE
        start_time = time.time()
        result = engine.process_file(file_stream, filename)
        duration = time.time() - start_time

        # 5. Report
        print("\n" + "="*40)
        print(f"   VISION REPORT v15.0")
        print("="*40)
        print(f"⏱️  Time Taken: {duration:.3f}s")
        print(f"📂 Filename:   {filename}")
        print(f"📊 Status:     {result['status']}")
        
        if result['status'] == 'SUCCESS':
             print(f"✅ Amount:     ₹{result['amount']}")
             print(f"🔍 UTR:        {result['utr']}")
        else:
             print(f"❌ Reason:     {result.get('reason')}")
             print(f"⚠️ Raw Amount: {result.get('amount')}")
             print(f"⚠️ Raw UTR:    {result.get('utr')}")

        print("="*40)

    except Exception as e:
        print(f"[CRITICAL FAIL] Test Script Crashed: {e}")

if __name__ == "__main__":
    test_ocr_pipeline()