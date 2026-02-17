import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.vision_engine import VisionEngine

def run_diagnostics(image_path):
    # 1. Resolve Path
    if not os.path.isabs(image_path):
        # Check relative to current working directory
        image_path = os.path.join(os.getcwd(), image_path)

    print(f"--- DIAGNOSTICS TARGET: {os.path.basename(image_path)} ---")
    
    if not os.path.exists(image_path):
        print(f"❌ CRITICAL: File not found at {image_path}")
        print("   Tip: Drag the image into the terminal to get the full path.")
        return

    # 2. Init Engine
    print("   [INIT] Loading docTR Model (ResNet-50)...")
    engine = VisionEngine(debug_mode=True)

    # 3. Process
    with open(image_path, 'rb') as f:
        print("   [EXEC] Scanning...")
        result = engine.process_file(f, os.path.basename(image_path))
    
    # 4. Report
    print("\n" + "="*40)
    print(f"STATUS: {result['status']}")
    if result['status'] == 'FAILED':
        print(f"REASON: {result['reason']}")
    else:
        print(f"💰 AMOUNT: ₹{result['amount']}")
        print(f"🆔 UTR   : {result['utr']}")
    print("="*40 + "\n")

if __name__ == "__main__":
    # Allow passing filename as argument: python test_day4.py my_image.jpg
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    else:
        # Default fallback
        target_file = "test_image.jpg"
        
    run_diagnostics(target_file)