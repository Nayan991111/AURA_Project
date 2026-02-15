import threading
import time
from src.services.drive_service import DriveService
from src.services.vision_engine import VisionEngine

class AuditManager:
    """
    TANK MODE: Single-threaded, high-stability processor.
    Prioritizes connection health over raw speed.
    """
    def __init__(self, log_callback, finished_callback):
        self.log_callback = log_callback
        self.finished_callback = finished_callback
        self.is_running = False
        self._stop_event = threading.Event()
        
        self.drive_service = None
        self.vision_engine = None
        self.stats = {'verified': 0, 'manual': 0, 'failed': 0, 'total_amt': 0.0, 'scanned': 0}

    def start_audit(self, drive_link):
        if self.is_running: return
        self.is_running = True
        self._stop_event.clear()
        
        # Run in background thread so UI doesn't freeze
        threading.Thread(target=self._run_sequential_audit, args=(drive_link,), daemon=True).start()

    def stop_audit(self):
        self.log_callback("[SYSTEM] Stopping audit process...")
        self._stop_event.set()

    def _run_sequential_audit(self, drive_link):
        try:
            # 1. Initialization
            self.log_callback("[INIT] Booting Tank Mode (Sequential Processing)...")
            if not self.vision_engine: self.vision_engine = VisionEngine()
            if not self.drive_service: self.drive_service = DriveService()

            # 2. Resolve Target
            self.log_callback("[DRIVE] Resolving Link...")
            folder_id = self.drive_service.extract_folder_id(drive_link)
            folder_name = self.drive_service.get_folder_name(folder_id)
            self.log_callback(f"[TARGET] {folder_name}")

            # 3. List Files
            files = self.drive_service.list_files_recursive(folder_id)
            if not files:
                self.log_callback("[WARN] No files found.")
                return

            self.log_callback(f"[SCAN] Found {len(files)} files. Starting Sequence...")
            
            # 4. Sequential Processing Loop (The Stabilizer)
            self.stats = {'verified': 0, 'manual': 0, 'failed': 0, 'total_amt': 0.0, 'scanned': 0}
            
            for i, file_meta in enumerate(files):
                if self._stop_event.is_set(): 
                    self.log_callback("[WARN] Audit Aborted by User.")
                    break
                
                # A. Download (With Retry Logic)
                self.log_callback(f"\n[PROC] ({i+1}/{len(files)}) {file_meta['name']}...")
                file_stream = self._download_safe(file_meta['id'])
                
                if not file_stream:
                    self.log_callback(f"   [ERR] Skipped due to download failure.")
                    self.stats['failed'] += 1
                    continue

                # B. Analyze
                result = self.vision_engine.process_file(file_stream, file_meta['name'])
                
                # C. Report
                self._handle_result(result, file_meta['name'])
                
                # D. Cooldown (Prevents SSL Choking)
                time.sleep(0.5)

            # 5. Final Report
            self._print_summary(folder_name, len(files))

        except Exception as e:
            self.log_callback(f"\n[CRITICAL ERROR] {str(e)}")
        finally:
            self.is_running = False
            self.finished_callback()

    def _download_safe(self, file_id):
        """Downloads with retries and backoff."""
        for attempt in range(3):
            try:
                return self.drive_service.download_file_to_memory(file_id)
            except Exception as e:
                self.log_callback(f"   [RETRY] Network blip... ({attempt+1}/3)")
                time.sleep(2) # Wait 2 seconds before retry
        return None

    def _handle_result(self, result, filename):
        status = result['status']
        amt = result.get('amount', 0.0)
        utr = result.get('utr', 'N/A')
        reason = result.get('reason', 'No recognizable text/data found')
        
        self.stats['scanned'] += 1

        if status == 'SUCCESS':
            self.stats['verified'] += 1
            self.stats['total_amt'] += amt
            self.log_callback(f"   [OK] Verified: ₹{amt} | UTR: {utr}")
        elif status == 'MANUAL_REVIEW':
            self.stats['manual'] += 1
            self.log_callback(f"   [?] Review Needed: Found ₹{amt} but no UTR.")
        else:
            self.stats['failed'] += 1
            self.log_callback(f"   [X] Failed: {reason}")

    def _print_summary(self, folder_name, total_files):
        self.log_callback("\n" + "="*40)
        self.log_callback(f"AUDIT COMPLETE: {folder_name}")
        self.log_callback(f"Scanned: {self.stats['scanned']} / {total_files}")
        self.log_callback(f"Verified: {self.stats['verified']}")
        self.log_callback(f"Review:   {self.stats['manual']}")
        self.log_callback(f"Failed:   {self.stats['failed']}")
        self.log_callback(f"TOTAL:    ₹{self.stats['total_amt']:,.2f}")
        self.log_callback("="*40)