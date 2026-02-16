import threading
import time
from src.services.drive_service import DriveService
from src.services.vision_engine import VisionEngine

class AuditManager:
    """
    TANK MODE MANAGER (Day 12 Final)
    - Sequential Processing (Safe for SSL)
    - Robust Error Handling
    - Thread-safe Callbacks
    """
    def __init__(self, log_callback, finished_callback):
        self.log_callback = log_callback
        self.finished_callback = finished_callback
        self.is_running = False
        self._stop_event = threading.Event()
        
        # Lazy Loading to prevent GUI freeze on init
        self.drive_service = None
        self.vision_engine = None
        self.stats = {'verified': 0, 'manual': 0, 'failed': 0, 'total_amt': 0.0, 'scanned': 0}

    def start_audit(self, drive_link):
        if self.is_running: return
        self.is_running = True
        self._stop_event.clear()
        
        # Launch the Tank in a separate thread
        threading.Thread(target=self._run_tank_process, args=(drive_link,), daemon=True).start()

    def stop_audit(self):
        self.log_callback("[SYSTEM] Abort signal received...")
        self._stop_event.set()

    def _run_tank_process(self, drive_link):
        try:
            # 1. Warmup
            self.log_callback("[INIT] Engaging Tank Mode (Sequential Engine)...")
            self.log_callback("[INIT] Loading Vision Models (Apple Silicon Optimized)...")
            
            if not self.vision_engine: self.vision_engine = VisionEngine()
            if not self.drive_service: self.drive_service = DriveService()

            # 2. Target Acquisition
            self.log_callback("[DRIVE] Resolving Target Link...")
            try:
                folder_id = self.drive_service.extract_folder_id(drive_link)
                folder_name = self.drive_service.get_folder_name(folder_id)
                self.log_callback(f"[TARGET] Lock on: {folder_name}")
            except Exception as e:
                self.log_callback(f"[ERROR] Invalid Link: {e}")
                return

            # 3. Reconnaissance (List Files)
            self.log_callback("[SCAN] Mapping file structure...")
            files = self.drive_service.list_files_recursive(folder_id)
            
            if not files:
                self.log_callback("[WARN] Target is empty or access denied.")
                return

            total_files = len(files)
            self.log_callback(f"[SCAN] Found {total_files} assets. Starting Verification Loop.")
            
            # 4. The Loop (Sequential Stability)
            self.stats = {'verified': 0, 'manual': 0, 'failed': 0, 'total_amt': 0.0, 'scanned': 0}
            
            for i, file_meta in enumerate(files):
                if self._stop_event.is_set(): 
                    self.log_callback("[WARN] Audit manually stopped.")
                    break
                
                self.log_callback(f"\n[PROC] [{i+1}/{total_files}] Processing: {file_meta['name']}")
                
                # A. Download
                file_stream = self._download_with_backoff(file_meta['id'])
                if not file_stream:
                    self.stats['failed'] += 1
                    continue

                # B. Vision Analysis (The Guillotine)
                result = self.vision_engine.process_file(file_stream, file_meta['name'])
                
                # C. Result Handling
                self._handle_result(result)
                
                # D. Cleanup & Throttle (Crucial for M4 Network Stability)
                file_stream.close()
                del file_stream
                time.sleep(0.2) # Micro-sleep to allow SSL socket recycle

            # 5. Mission Debrief
            self._print_final_report(folder_name, total_files)

        except Exception as e:
            self.log_callback(f"\n[CRITICAL FAILURE] {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_running = False
            self.finished_callback()

    def _download_with_backoff(self, file_id):
        """Exponential Backoff for Google API Network Blips."""
        retries = 3
        for attempt in range(retries):
            try:
                return self.drive_service.download_file_to_memory(file_id)
            except Exception as e:
                wait = (attempt + 1) * 2
                self.log_callback(f"   [NET] Download stutter ({e}). Retrying in {wait}s...")
                time.sleep(wait)
        self.log_callback("   [ERR] Download failed after 3 attempts.")
        return None

    def _handle_result(self, result):
        self.stats['scanned'] += 1
        status = result['status']
        amt = result.get('amount', 0.0)
        utr = result.get('utr', 'N/A')
        
        if status == 'SUCCESS':
            self.stats['verified'] += 1
            self.stats['total_amt'] += amt
            self.log_callback(f"   [OK] Verified: ₹{amt:,.2f} | UTR: {utr}")
            
        elif status == 'MANUAL_REVIEW':
            self.stats['manual'] += 1
            self.log_callback(f"   [?] Review Required: {result.get('reason')}")
            
        else:
            self.stats['failed'] += 1
            self.log_callback(f"   [X] Failed: {result.get('reason')}")

    def _print_final_report(self, folder_name, total):
        s = self.stats
        report = [
            "\n" + "="*40,
            f"AUDIT COMPLETE: {folder_name}",
            f"Files Scanned: {s['scanned']}/{total}",
            "-"*40,
            f"✅ Verified:     {s['verified']}",
            f"⚠️ Review Needed: {s['manual']}",
            f"❌ Failed:       {s['failed']}",
            "-"*40,
            f"💰 TOTAL VALUE:  ₹{s['total_amt']:,.2f}",
            "="*40
        ]
        for line in report:
            self.log_callback(line)