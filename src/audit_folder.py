import sys
import os
import re
import time

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path: sys.path.append(project_root)

from src.services.drive_manager import DriveManager
from src.services.vision_engine import VisionEngine
from src.services.sheet_manager import SheetManager

class AuditSession:
    """
    The Conductor. Orchestrates the flow between Drive, Vision, and Sheets.
    "Iron Dome" Policy: 
    1. Load Global Ledger to RAM.
    2. Download Image to RAM.
    3. Extract UTR.
    4. Cross-reference immediately.
    """
    
    def __init__(self, sheet_id: str):
        print("\n[INIT] Booting AURA System on M4 Silicon...")
        
        # 1. Initialize The Memory (Global Ledger)
        self.memory = SheetManager(sheet_id)
        
        # 2. Initialize The Brain (Vision Engine)
        self.brain = VisionEngine()
        
        # 3. Initialize The Hands (Drive Interceptor)
        self.drive = DriveManager()

    def extract_folder_id(self, url: str) -> str:
        """Sanitizes Google Drive Links to extract the Folder ID."""
        # Matches patterns like folders/1A2B3C... or id=1A2B3C...
        patterns = [
            r'folders\/([a-zA-Z0-9\-_]+)',
            r'id=([a-zA-Z0-9\-_]+)'
        ]
        for p in patterns:
            match = re.search(p, url)
            if match: return match.group(1)
        return url # Assume user pasted raw ID if no regex match

    def start_audit(self, folder_link: str):
        # --- PHASE 1: RAM PRE-CACHING ---
        print("\n--- PHASE 1: SYNCHRONIZING MEMORY ---")
        self.memory.load_ledger() # Downloads ~10,000 UTRs to RAM in <2s

        # --- PHASE 2: DRIVE RECONNAISSANCE ---
        folder_id = self.extract_folder_id(folder_link)
        print(f"\n--- PHASE 2: INTERCEPTING DRIVE FOLDER [{folder_id}] ---")
        
        # We need to list files. 
        # Note: Assuming DriveManager has a list_files method as per Day 2 spec.
        # Since Day 2 code wasn't fully provided in prompt, I will use a direct service call 
        # pattern here to ensure it works with the 'Essential Snippets' provided.
        files = self._fetch_files_recursive(folder_id)
        
        if not files:
            print("[ALERT] No processable images/PDFs found in this folder.")
            return

        print(f"   [TARGET ACQUIRED] Found {len(files)} potential receipts.")

        # --- PHASE 3: THE IRON DOME LOOP ---
        print("\n--- PHASE 3: EXECUTING AUDIT LOOP ---")
        print(f"{'STATUS':<15} | {'UTR':<15} | {'AMOUNT':<10} | {'FILENAME'}")
        print("-" * 70)

        results_summary = {'SUCCESS': 0, 'DUPLICATE': 0, 'FAILED': 0, 'REVIEW': 0}

        for file in files:
            file_name = file['name']
            file_id = file['id']

            # A. The Brain Analysis
            # VisionEngine returns: {'amount': float, 'utr': str, 'status': str}
            data = self.brain.analyze_file(file_id)

            # B. The Iron Dome Logic (Fraud Check)
            final_status = data['status']
            
            # Logic: If OCR found a UTR, we MUST check the Ledger
            if data['utr']:
                is_fraud = self.memory.is_duplicate(data['utr'])
                if is_fraud:
                    final_status = 'DUPLICATE' # The dreaded Red Flag
                    data['status'] = 'DUPLICATE'

            # C. Reporting (Real-Time Terminal Dashboard)
            self._print_log(final_status, data.get('utr', 'N/A'), data.get('amount', 0), file_name)
            
            # Update Stats
            if final_status == 'SUCCESS': results_summary['SUCCESS'] += 1
            elif final_status == 'DUPLICATE': results_summary['DUPLICATE'] += 1
            elif final_status == 'FAILED': results_summary['FAILED'] += 1
            else: results_summary['REVIEW'] += 1

        # --- PHASE 4: MISSION REPORT ---
        print("\n" + "="*30)
        print("       MISSION COMPLETE       ")
        print("="*30)
        print(f"Total Scanned : {len(files)}")
        print(f"Verified (OK) : {results_summary['SUCCESS']}")
        print(f"FRAUD DETECTED: {results_summary['DUPLICATE']}")
        print(f"Manual Review : {results_summary['REVIEW']}")
        print(f"Failed/Blurry : {results_summary['FAILED']}")
        print("="*30 + "\n")

    def _fetch_files_recursive(self, folder_id):
        """
        Helper to interact with DriveManager's service directly 
        if list_files isn't exposed in the snippet provided.
        """
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
                
                items = response.get('files', [])
                for item in items:
                    # If folder, recurse (Basic implementation for depth)
                    if item['mimeType'] == 'application/vnd.google-apps.folder':
                        results.extend(self._fetch_files_recursive(item['id']))
                    elif any(m in item['mimeType'] for m in ['image/', 'pdf']):
                        results.append(item)
                        
                page_token = response.get('nextPageToken')
                if not page_token: break
        except Exception as e:
            print(f"[ERROR] Drive Crawl Failed: {e}")
        
        return results

    def _print_log(self, status, utr, amount, filename):
        # Color coding for terminal
        RESET = "\033[0m"
        RED = "\033[91m"
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        BLUE = "\033[94m"

        color = RESET
        if status == 'SUCCESS': color = GREEN
        elif status == 'DUPLICATE': color = RED
        elif status == 'MANUAL_REVIEW': color = YELLOW
        elif status == 'FAILED': color = BLUE

        # Truncate filename for clean UI
        short_name = (filename[:20] + '..') if len(filename) > 20 else filename
        safe_utr = utr if utr else "---"
        
        print(f"{color}[{status}]    {safe_utr:<15} ₹{amount:<9} {short_name}{RESET}")

if __name__ == "__main__":
    # Hardcoded for Dev Testing (Day 6) - Replace these with your actual IDs during run
    # You can leave these blank, the script will prompt you.
    print("--- AURA DEV CONSOLE (DAY 6) ---")
    
    input_sheet_id = input("Enter Master Ledger Sheet ID: ").strip()
    input_folder_link = input("Enter Target Drive Folder Link: ").strip()
    
    if input_sheet_id and input_folder_link:
        session = AuditSession(input_sheet_id)
        session.start_audit(input_folder_link)
    else:
        print("[ERROR] Missing Inputs. Aborting.")