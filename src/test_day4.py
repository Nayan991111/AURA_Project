import sys
import os

# --- PATH FIX V2 (ROBUST) ---
# Get the directory containing this script (AURA_Project/src)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the project root (AURA_Project)
project_root = os.path.dirname(current_dir)
# Add root to Python's search path
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# -----------------------------

from src.services.vision_engine import VisionEngine

def test_ocr_pipeline():
    print("--- [DAY 4] VISION ENGINE DIAGNOSTICS ---")
    
    # 1. Initialize
    try:
        engine = VisionEngine()
        print("[OK] VisionEngine Initialized")
    except Exception as e:
        print(f"[FAIL] Could not init VisionEngine: {e}")
        return

    # 2. Input
    raw_input = input("Enter a Google Drive Link (Folder or File) or ID: ").strip()
    
    if not raw_input:
        print("[SKIP] No input provided.")
        return

    # Smart ID Resolution
    target_id = raw_input
    
    # 2a. Try to extract ID if it's a URL
    # (We use the engine's internal drive instance helper)
    extracted = engine.drive.extract_folder_id(raw_input)
    if extracted:
        target_id = extracted
        print(f"[INFO] Extracted ID: {target_id}")

    # 2b. Check if it's a Folder and Auto-Resolve an Image
    print("[...] Checking if ID is a Folder...")
    try:
        # We attempt to list files. If target_id is a file, this usually returns empty or error, handled below.
        files = engine.drive.list_files(target_id, recursive=False)
        
        # Check if we actually got a list of files back
        if files and isinstance(files, list) and len(files) > 0:
            print(f"[INFO] Detected FOLDER containing {len(files)} files.")
            found_image = None
            # Prioritize standard images over PDF for this test
            for f in files:
                if f['mime'] in ['image/jpeg', 'image/png', 'image/heic']:
                    found_image = f
                    break
            
            if found_image:
                print(f"[INFO] Auto-selected image: {found_image['name']} ({found_image['id']})")
                target_id = found_image['id']
            else:
                print("[WARN] Folder found, but contains no valid images (JPG/PNG).")
    except Exception as e:
        # If list_files fails, it's likely because target_id is already a FILE ID, not a folder.
        # We ignore the error and proceed to analyze it as a file.
        pass

    # 3. Run Analysis
    print(f"\n[...] Analyzing Target ID: {target_id}...")
    result = engine.analyze_file(target_id)

    # 4. Report
    print("\n--- ANALYSIS REPORT ---")
    status = result.get('status', 'UNKNOWN')
    print(f"STATUS: {status}")
    
    if status == 'FAILED':
        print(f"REASON: {result.get('reason')}")
    else:
        print(f"AMOUNT: ₹{result.get('amount')}")
        print(f"UTR/ID: {result.get('utr')}")
        print(f"DATE:   {result.get('timestamp')}")
        
    print("-" * 30)
    print("RAW TEXT SAMPLE (First 100 chars):")
    print(str(result.get('extracted_text', ''))[:100].replace('\n', ' '))
    print("-" * 30)

if __name__ == "__main__":
    test_ocr_pipeline()