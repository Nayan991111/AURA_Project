from src.services.telemetry_service import TelemetryService
import threading
import time
from src.services.drive_service import DriveService
from src.services.vision_engine import VisionEngine


class AuditManager:
    """
    AURA AUDIT MANAGER v2.0 (Day 16 Compliance Hardened)

    Fixes:
    - Eliminates UI financial calculation from log parsing
    - Structured metric updates
    - No double counting
    - Thread-safe
    - Sequential stability mode
    """

    def __init__(self, log_callback, finished_callback):
        self.log_callback = log_callback
        self.finished_callback = finished_callback

        self.is_running = False
        self._stop_event = threading.Event()

        self.drive_service = None
        self.vision_engine = None

        self._reset_stats()

        # Thread lock for financial integrity
        self._stats_lock = threading.Lock()

    # ---------------------------
    # PUBLIC ENTRY
    # ---------------------------

    def start_audit(self, drive_link):
        if self.is_running:
            return

        self.is_running = True
        self._stop_event.clear()

        threading.Thread(
            target=self._run_tank_process,
            args=(drive_link,),
            daemon=True
        ).start()

    def stop_audit(self):
        self.log_callback("[SYSTEM] Abort signal received...")
        self._stop_event.set()

    # ---------------------------
    # CORE ENGINE
    # ---------------------------

    def _run_tank_process(self, drive_link):
        try:
            self._reset_stats()

            self.log_callback("[INIT] Engaging Tank Mode (Sequential Engine)...")
            self.log_callback("[INIT] Loading Vision Models...")

            if not self.vision_engine:
                self.vision_engine = VisionEngine()

            if not self.drive_service:
                self.drive_service = DriveService()

            # Resolve folder
            self.log_callback("[DRIVE] Resolving Target Link...")
            folder_id = self.drive_service.extract_folder_id(drive_link)
            folder_name = self.drive_service.get_folder_name(folder_id)
            self.log_callback(f"[TARGET] Lock on: {folder_name}")

            # List files
            self.log_callback("[SCAN] Mapping file structure...")
            files = self.drive_service.list_files_recursive(folder_id)

            if not files:
                self.log_callback("[WARN] Target is empty or access denied.")
                return

            total_files = len(files)
            self.log_callback(f"[SCAN] Found {total_files} assets. Starting Verification Loop.")

            # Sequential loop
            for i, file_meta in enumerate(files):

                if self._stop_event.is_set():
                    self.log_callback("[WARN] Audit manually stopped.")
                    break

                self.log_callback(f"\n[PROC] [{i+1}/{total_files}] Processing: {file_meta['name']}")

                file_stream = self._download_with_backoff(file_meta['id'])
                if not file_stream:
                    self._increment_failed()
                    continue

                result = self.vision_engine.process_file(file_stream, file_meta['name'])

                self._handle_result(result)

                file_stream.close()
                del file_stream

                time.sleep(0.2)

            self._print_final_report(folder_name, total_files)

        except Exception as e:
            self.log_callback(f"\n[CRITICAL FAILURE] {str(e)}")
        finally:
            self.is_running = False
            self.finished_callback()

    # ---------------------------
    # DOWNLOAD SAFETY
    # ---------------------------

    def _download_with_backoff(self, file_id):
        retries = 3
        for attempt in range(retries):
            try:
                return self.drive_service.download_file_to_memory(file_id)
            except Exception as e:
                wait = (attempt + 1) * 2
                self.log_callback(f"   [NET] Download stutter. Retrying in {wait}s...")
                time.sleep(wait)

        self.log_callback("   [ERR] Download failed after retries.")
        return None

    # ---------------------------
    # RESULT HANDLING (CRITICAL FIX)
    # ---------------------------

    def _handle_result(self, result):

        status = result.get('status')
        amt = float(result.get('amount', 0.0))
        utr = result.get('utr', 'N/A')

        with self._stats_lock:
            self.stats['scanned'] += 1

            if status == 'SUCCESS':
                self.stats['verified'] += 1
                self.stats['total_amt'] += amt

                # 🔥 Structured metric update (no parsing required)
                self.log_callback({
                    "event": "SUCCESS",
                    "amount": amt
                })

                self.log_callback(f"   [OK] Verified: ₹{amt:,.2f} | UTR: {utr}")

            elif status == 'MANUAL_REVIEW':
                self.stats['manual'] += 1
                self.log_callback({
                    "event": "MANUAL"
                })
                self.log_callback(f"   [?] Review Required")

            else:
                self.stats['failed'] += 1
                self.log_callback({
                    "event": "FAILED"
                })
                self.log_callback(f"   [X] Failed")

    # ---------------------------
    # REPORTING
    # ---------------------------

    def _print_final_report(self, folder_name, total):

        s = self.stats

        report_lines = [
            "\n" + "=" * 40,
            f"AUDIT COMPLETE: {folder_name}",
            f"Files Scanned: {s['scanned']}/{total}",
            "-" * 40,
            f"✅ Verified:     {s['verified']}",
            f"⚠️ Review Needed: {s['manual']}",
            f"❌ Failed:       {s['failed']}",
            "-" * 40,
            f"💰 TOTAL VALUE:  ₹{s['total_amt']:,.2f}",
            "=" * 40
        ]

        for line in report_lines:
            self.log_callback(line)

        # Telemetry
        try:
            telemetry = TelemetryService(
                spreadsheet_id="1UWcUhHrJx6jokEaSOd-lVthecqvnLpiSKuFX2p5zuiQ"
            )
            telemetry.send_audit_summary(folder_name, s)
        except Exception:
            self.log_callback("[WARN] Telemetry initiation failed.")

    # ---------------------------
    # INTERNAL SAFE HELPERS
    # ---------------------------

    def _increment_failed(self):
        with self._stats_lock:
            self.stats['scanned'] += 1
            self.stats['failed'] += 1

            self.log_callback({
                "event": "FAILED"
            })

    def _reset_stats(self):
        self.stats = {
            'verified': 0,
            'manual': 0,
            'failed': 0,
            'total_amt': 0.0,
            'scanned': 0
        }