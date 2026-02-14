import sys
import os
import re

# --- ROBUST PATH SETUP ---
# This ensures imports work whether the file is in src/ or src/utils/
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
# Traverse up until we are just outside 'src'
while os.path.basename(project_root) != 'src' and len(project_root) > 4:
    project_root = os.path.dirname(project_root)
project_root = os.path.dirname(project_root) # Go one level up from src
if project_root not in sys.path: sys.path.append(project_root)
# -------------------------

from src.services.drive_manager import DriveManager
from src.services.vision_engine import VisionEngine
from src.services.sheet_manager import SheetManager
from src.services.session_manager import SessionManager

class AuditSession:
    """
    Day 7: The Black Box Update.
    Orchestrates Drive, Vision, Sheets, and now the SQLite Session Recorder.
    """
    def __init__(self, sheet_id: str):
        print("\n[INIT] Booting AURA System on M4 Silicon...")
        self.memory = SheetManager(sheet_id)
        self.brain = VisionEngine()
        self.drive = DriveManager()
        self.recorder = SessionManager() # The Black Box Database

    def extract_folder_id(self, url: str) -> str:
        """Sanitizes Google Drive Links to extract the Folder ID."""
        patterns = [
            r'folders\/([a-zA-Z0-9\-_]+)',
            r'id=([a-zA-Z0-9\-_]+)'
        ]
        for p in patterns:
            match = re.search(p, url)
            if match: return match.group(1)
        return url

    def start_audit(self, folder_link: str):
        # 1. Sync Ledger (The "Memory")
        self.memory.load_ledger()
        
        # 2. Resolve Target & Identity
        folder_id = self.extract_folder_id(folder_link)
        
        # [NEW] Attempt to identify the Intern Name from the Folder Name
        try:
            folder_meta = self.drive.service.files().get(fileId=folder_id, fields="name").execute()
            intern_name = folder_meta.get('name', 'Unknown_Intern')
            print(f"\n--- PHASE 2: INTERCEPTING DRIVE FOLDER [{folder_id}] ---")
            print(f"   [IDENTITY] Audit Target: {intern_name}")
        except Exception as e:
            print(f"   [WARN] Could not identify intern name: {e}")
            intern_name = "Unknown_Intern"

        # 3. Fetch Files
        files = self._fetch_files_recursive(folder_id)
        print(f"   [TARGET ACQUIRED] Found {len(files)} potential receipts.")

        print("\n--- PHASE 3: EXECUTING AUDIT LOOP ---")
        
        # 4. The Audit Loop
        for file in files:
            # A. Analysis (The Brain)
            data = self.brain.analyze_file(file['id'])
            
            # B. The Iron Dome (Duplicate Check)
            if data['utr']:
                if self.memory.is_duplicate(data['utr']):
                    data['status'] = 'DUPLICATE'

            # C. The Black Box (Atomic Logging to SQLite)
            # This persists the result immediately, even if the script crashes later.
            self.recorder.log_transaction(
                intern_name=intern_name,
                folder_id=folder_id,
                file_name=file['name'],
                utr=data.get('utr'),
                amount=data.get('amount'),
                status=data.get('status')
            )

            # D. Live Feed (Terminal Output)
            self._print_log(data.get('status'), data.get('utr', 'N/A'), data.get('amount', 0), file['name'])

        # 5. Session End Summary
        self._print_summary(folder_id)

    def _fetch_files_recursive(self, folder_id):
        results = []
        page_token = None
        query = f"'{folder_id}' in parents and trashed = false"
        try:
            while True:
                response = self.drive.service.files().list(
                    q=query, 
                    fields="nextPageToken, files(id, name, mimeType)", 
                    pageToken=page_token
                ).execute()
                
                for item in response.get('files', []):
                    if item['mimeType'] == 'application/vnd.google-apps.folder':
                        results.extend(self._fetch_files_recursive(item['id']))
                    elif any(m in item['mimeType'] for m in ['image/', 'pdf']):
                        results.append(item)
                
                page_token = response.get('nextPageToken')
                if not page_token: break
        except Exception: pass
        return results

    def _print_log(self, status, utr, amount, filename):
        RESET, RED, GREEN, YELLOW, BLUE = "\033[0m", "\033[91m", "\033[92m", "\033[93m", "\033[94m"
        color = RESET
        if status == 'SUCCESS': color = GREEN
        elif status == 'DUPLICATE': color = RED
        elif status == 'MANUAL_REVIEW': color = YELLOW
        elif status == 'FAILED': color = BLUE
        
        # Truncate filename for cleaner UI
        clean_fname = (filename[:18] + '..') if len(filename) > 20 else filename
        # Safely handle None types for printing
        safe_utr = str(utr) if utr else "N/A"
        safe_amt = str(amount) if amount else "0"
        
        print(f"{color}[{status}]    {safe_utr:<15} ₹{safe_amt:<9} {clean_fname}{RESET}")

    def _print_summary(self, folder_id):
        """Reads back from the Black Box DB to show final stats"""
        stats = self.recorder.get_session_stats(folder_id)
        print("\n" + "="*40)
        print("       MISSION COMPLETE: SESSION SUMMARY       ")
        print("="*40)
        total_verified = 0.0
        
        # stats format: [(status, count, sum_amount), ...]
        for row in stats:
            status, count, total_amt = row
            amt = total_amt if total_amt else 0
            print(f"   {status:<15}: {count:3} files  (₹ {amt:,.2f})")
            if status == 'SUCCESS': total_verified = amt
        
        print("-" * 40)
        print(f"   [TOTAL VERIFIED]: ₹ {total_verified:,.2f}")
        print("="*40 + "\n")

if __name__ == "__main__":
    print("--- AURA DEV CONSOLE (DAY 7) ---")
    s_id = input("Enter Master Ledger Sheet ID: ").strip()
    f_link = input("Enter Target Drive Folder Link: ").strip()
    if s_id and f_link: 
        AuditSession(s_id).start_audit(f_link)