import sys
import os
import re
from typing import Set

# --- PATH FIX ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path: sys.path.append(project_root)

from googleapiclient.discovery import build
from src.services.auth_manager import AuthManager

class SheetManager:
    """
    The 'Memory' of AURA.
    Connects to the Master Ledger to fetch historical UTRs/Transaction IDs
    to prevent Duplicate Fraud.
    """
    
    def __init__(self, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.auth = AuthManager()
        self.creds = self.auth.get_credentials()
        self.service = build('sheets', 'v4', credentials=self.creds)
        
        # The 'Iron Set' - A hash set for O(1) duplicate lookups
        self.ledger_utrs: Set[str] = set()
        self.loaded = False

    def _normalize_utr(self, utr: str) -> str:
        """
        Strips all non-alphanumeric characters for strict comparison.
        Ex: 'UPI-12345' -> '12345'
        Ex: ' 12345 '   -> '12345'
        """
        if not utr: return ""
        # Remove anything that isn't a letter or number
        return re.sub(r'[^A-Za-z0-9]', '', str(utr)).strip()

    def load_ledger(self, range_name: str = 'Sheet1!A:Z'):
        """
        Downloads the Master Ledger into RAM.
        We scan ALL columns to be safe against interns pasting UTRs in the wrong place.
        """
        print(f"   [MEMORY] Syncing with Master Ledger ({self.spreadsheet_id})...")
        try:
            sheet = self.service.spreadsheets()
            result = sheet.values().get(spreadsheetId=self.spreadsheet_id, range=range_name).execute()
            rows = result.get('values', [])

            count = 0
            for row in rows:
                for cell in row:
                    clean_val = self._normalize_utr(cell)
                    # Filter: Only keep strings that look like transaction IDs (Length > 6)
                    # This avoids caching words like "Verified" or "Pending"
                    if len(clean_val) > 6 and not clean_val.isalpha(): 
                        self.ledger_utrs.add(clean_val)
                        count += 1
            
            self.loaded = True
            print(f"   [SUCCESS] Ledger Synced. {count} historic transactions cached in RAM.")
            
        except Exception as e:
            print(f"   [CRITICAL FAIL] Could not load Master Ledger: {e}")
            raise e

    def is_duplicate(self, candidate_utr: str) -> bool:
        """
        Checks if the candidate UTR exists in the Master Ledger.
        Returns True if it is a DUPLICATE (Fraud/Error).
        """
        if not self.loaded:
            print("   [WARN] Ledger not loaded. Call load_ledger() first.")
            return False 
            
        clean_candidate = self._normalize_utr(candidate_utr)
        
        # O(1) Lookup Speed
        if clean_candidate in self.ledger_utrs:
            return True
            
        return False

# --- INTEGRATION TEST ---
if __name__ == "__main__":
    print("--- TESTING IRON DOME LEDGER ---")
    
    # I used the ID from your screenshot/code snippet
    TEST_ID = '1UWcUhHrJx6jokEaSOd-lVthecqvnLpiSKuFX2p5zuiQ' 
    
    # 1. Initialize
    manager = SheetManager(TEST_ID)
    
    # 2. Load Memory
    manager.load_ledger()
    
    # 3. Test Fraud Detection
    # Change '123456789' to a real UTR from your sheet to test a TRUE POSITIVE
    fake_utr = "123456789" 
    
    if manager.is_duplicate(fake_utr):
        print(f"[RESULT] UTR '{fake_utr}' found in Ledger? -> YES (DUPLICATE)")
    else:
        print(f"[RESULT] UTR '{fake_utr}' found in Ledger? -> NO (NEW DONATION)")