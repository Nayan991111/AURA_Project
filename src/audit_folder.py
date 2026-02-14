import sys, os, re
import time
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Robust Path Setup
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
while os.path.basename(project_root) != 'src' and len(project_root) > 4:
    project_root = os.path.dirname(project_root)
project_root = os.path.dirname(project_root)
if project_root not in sys.path: sys.path.append(project_root)

from src.services.drive_manager import DriveManager
from src.services.vision_engine import VisionEngine
from src.services.sheet_manager import SheetManager
from src.services.session_manager import SessionManager
from src.services.reporter import ReportGenerator  # <--- NEW IMPORT

# Thread-Safe Locks
print_lock = threading.Lock()
stats_lock = threading.Lock()

# Thread-Local Storage
thread_local = threading.local()

def get_thread_safe_brain():
    if not hasattr(thread_local, "brain"):
        thread_local.brain = VisionEngine()
    return thread_local.brain

class AuditSession:
    def __init__(self, sheet_id: str):
        print("\n[INIT] Booting AURA System on M4 Silicon...")
        self.memory = SheetManager(sheet_id)
        self.drive = DriveManager() 
        self.recorder = SessionManager()
        self.reporter = ReportGenerator() # <--- NEW INSTANCE
        
        # Session State
        self.session_stats = {
            'SUCCESS': 0, 'DUPLICATE': 0, 'MANUAL_REVIEW': 0, 'FAILED': 0,
            'total_amt': 0.0, 'count': 0, 
            'date': datetime.datetime.now().strftime("%Y-%m-%d")
        }
        self.flagged_items = [] # <--- Stores details of bad files

    def extract_folder_id(self, url: str) -> str:
        patterns = [r'folders\/([a-zA-Z0-9\-_]+)', r'id=([a-zA-Z0-9\-_]+)']
        for p in patterns:
            match = re.search(p, url)
            if match: return match.group(1)
        return url

    def process_single_file(self, file_meta: dict, intern_name: str, folder_id: str):
        try:
            local_brain = get_thread_safe_brain()
            
            # 1. Vision Analysis
            data = local_brain.analyze_file(file_meta['id'])
            
            # Retry on Download Error
            if data.get('status') == 'FAILED' and data.get('reason') == 'Download Error':
                time.sleep(0.5) 
                data = local_brain.analyze_file(file_meta['id'])
            
            # 2. Duplicate Check
            if data.get('utr') and self.memory.is_duplicate(data['utr']):
                data['status'] = 'DUPLICATE'

            # 3. Logging
            self.recorder.log_transaction(
                intern_name=intern_name, folder_id=folder_id, file_name=file_meta['name'],
                utr=data.get('utr'), amount=data.get('amount'), status=data.get('status')
            )

            # 4. Update Stats & Collect Flags (Thread-Safe)
            with stats_lock:
                status = data.get('status', 'FAILED')
                amt = data.get('amount', 0)
                if status in self.session_stats:
                    self.session_stats[status] += 1
                self.session_stats['count'] += 1
                if status == 'SUCCESS':
                    self.session_stats['total_amt'] += amt
                
                # Capture Bad Files for Report
                if status in ['DUPLICATE', 'MANUAL_REVIEW', 'FAILED']:
                    self.flagged_items.append({
                        'file_name': file_meta['name'],
                        'status': status,
                        'amount': amt
                    })

            self._print_log_threadsafe(data.get('status'), data.get('utr'), data.get('amount'), file_meta['name'])
            return True

        except Exception as e:
            with print_lock:
                print(f"[CRITICAL ERROR] Thread crashed on {file_meta['name']}: {e}")
            return False

    def start_audit(self, folder_link: str):
        start_time = time.time()
        self.memory.load_ledger()
        
        folder_id = self.extract_folder_id(folder_link)
        try:
            folder_meta = self.drive.service.files().get(fileId=folder_id, fields="name").execute()
            intern_name = folder_meta.get('name', 'Unknown_Intern')
            print(f"\n--- PHASE 2: INTERCEPTING DRIVE FOLDER [{folder_id}] ---")
            print(f"   [IDENTITY] Audit Target: {intern_name}")
        except Exception: 
            intern_name = "Unknown_Intern"

        files = self._fetch_files_recursive(folder_id)
        print(f"   [TARGET ACQUIRED] Found {len(files)} potential receipts.")
        print("\n--- PHASE 3: EXECUTING PARALLEL AUDIT (5 THREADS) ---")
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(self.process_single_file, file, intern_name, folder_id) 
                for file in files
            ]
            for future in as_completed(futures): pass 

        duration = time.time() - start_time
        
        # FINAL REPORT GENERATION
        print("\n" + "="*40)
        report_text = self.reporter.generate_whatsapp_report(
            intern_name, self.session_stats, self.flagged_items
        )
        print(report_text)
        print("="*40)

    def _fetch_files_recursive(self, folder_id):
        results = []
        page_token = None
        query = f"'{folder_id}' in parents and trashed = false"
        try:
            while True:
                response = self.drive.service.files().list(
                    q=query, fields="nextPageToken, files(id, name, mimeType)", pageToken=page_token
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

    def _print_log_threadsafe(self, status, utr, amount, filename):
        RESET, RED, GREEN, YELLOW, BLUE = "\033[0m", "\033[91m", "\033[92m", "\033[93m", "\033[94m"
        color = RESET
        if status == 'SUCCESS': color = GREEN
        elif status == 'DUPLICATE': color = RED
        elif status == 'MANUAL_REVIEW': color = YELLOW
        elif status == 'FAILED': color = BLUE
        
        clean_fname = (filename[:18] + '..') if len(filename) > 20 else filename
        safe_utr = str(utr) if utr else "N/A"
        safe_amt = str(amount) if amount else "0"
        
        with print_lock:
            print(f"{color}[{status}]    {safe_utr:<15} ₹{safe_amt:<9} {clean_fname}{RESET}")

if __name__ == "__main__":
    print("--- AURA DEV CONSOLE (DAY 9 - REPORTING ENGINE) ---")
    s_id = input("Enter Master Ledger Sheet ID: ").strip()
    f_link = input("Enter Target Drive Folder Link: ").strip()
    if s_id and f_link: AuditSession(s_id).start_audit(f_link)