import time

from src.services.sheet_manager import SheetManager



# --- CONFIGURATION ---

# PASTE YOUR GOOGLE SHEET ID HERE

TEST_SHEET_ID = "1qE_wadgnmZPeAYWQ3oibIx5S-msGAipbWuyPzYi6ivQ" 



def test_ledger_connection():

    print("--- STARTING DAY 5 INTEGRATION TEST ---")

    

    # 1. Initialize

    print("[1] Initializing SheetManager...")

    try:

        ledger = SheetManager(TEST_SHEET_ID)

    except Exception as e:

        print(f"[FAIL] Init failed. Auth error? {e}")

        return



    # 2. Load Data

    print("[2] Loading Ledger Data (RAM Cache)...")

    start_time = time.time()

    # Note: We fetch the whole sheet to ensure we catch UTRs wherever they are

    ledger.load_ledger() 

    end_time = time.time()

    print(f"    -> Load Time: {end_time - start_time:.4f} seconds")



    # 3. Test Verification Logic

    # Replace this with a UTR you KNOW is in your sheet to test 'True'

    known_utr = "123456789012" 

    # Replace this with a random number

    new_utr = "999999999999"   



    print(f"[3] Checking Known Duplicate ({known_utr})...")

    if ledger.is_duplicate(known_utr):

        print(f"    [PASS] Correctly identified {known_utr} as a DUPLICATE.")

    else:

        print(f"    [FAIL] Failed to identify {known_utr}. Check your sheet data.")



    print(f"[4] Checking New Unique UTR ({new_utr})...")

    if not ledger.is_duplicate(new_utr):

        print(f"    [PASS] Correctly identified {new_utr} as NEW/UNIQUE.")

    else:

        print(f"    [FAIL] False Positive on {new_utr}.")



if __name__ == "__main__":

    test_ledger_connection()