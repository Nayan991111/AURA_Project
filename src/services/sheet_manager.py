import sys
import os

# --- PATH FIX: Add the project root to the python path ---
# This ensures we can import 'src' even when running this file directly
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)
# ---------------------------------------------------------

from googleapiclient.discovery import build
from src.services.auth_manager import AuthManager

class SheetManager:
    """
    Service to interact with Google Sheets.
    Uses AuthManager to handle credentials automatically.
    """
    def __init__(self):
        # 1. Get valid credentials from our AuthManager
        self.auth = AuthManager()
        self.creds = self.auth.get_credentials()
        
        # 2. Build the API Service
        if self.creds:
            self.service = build('sheets', 'v4', credentials=self.creds)
            self.sheet = self.service.spreadsheets()
        else:
            print("[ERROR] Could not initialize SheetManager: No credentials.")
            self.service = None

    def read_range(self, spreadsheet_id, range_name):
        """
        Reads data from a specific range.
        """
        if not self.service:
            return []

        try:
            result = self.sheet.values().get(
                spreadsheetId=spreadsheet_id, 
                range=range_name
            ).execute()
            
            return result.get('values', [])
            
        except Exception as e:
            print(f"[ERROR] Failed to read sheet: {e}")
            return []

# --- INTEGRATION TEST ---
if __name__ == "__main__":
    print("--- TESTING SHEET MANAGER ---")
    
    # YOUR TEST ID
    TEST_SPREADSHEET_ID = '1UWcUhHrJx6jokEaSOd-lVthecqvnLpiSKuFX2p5zuiQ' 
    TEST_RANGE = 'Sheet1!A1:D5'

    manager = SheetManager()
    data = manager.read_range(TEST_SPREADSHEET_ID, TEST_RANGE)
    
    if data:
        print(f"[SUCCESS] Retrieved {len(data)} rows:")
        for row in data:
            print(row)
    else:
        print("[WARN] No data found.")