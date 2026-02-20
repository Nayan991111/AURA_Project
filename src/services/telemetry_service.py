import threading
import datetime
from googleapiclient.discovery import build
from src.services.auth_manager import AuthManager
from src.services.profile_manager import ProfileManager

class TelemetryService:
    """
    ENTERPRISE TELEMETRY ENGINE
    Handles sending non-sensitive metadata (Scan counts, User ID) to the Master Ledger.
    Executes on a background daemon thread to ensure Zero UI Blocking.
    """
    def __init__(self, spreadsheet_id: str, sheet_name: str = "Telemetry"):
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name  # The specific Tab/Sheet name in your Google Sheet
        self.auth = AuthManager()
        self.profile_mgr = ProfileManager()

    def send_audit_summary(self, folder_name: str, stats: dict):
        """Fire-and-forget background push."""
        profile = self.profile_mgr.get_profile()
        if not profile:
            print("[TELEMETRY] No profile found. Skipping push.")
            return 

        # Spin up a daemon thread to prevent app hang on exit
        threading.Thread(
            target=self._push_to_sheets, 
            args=(profile, folder_name, stats), 
            daemon=True
        ).start()

    def _push_to_sheets(self, profile: dict, folder_name: str, stats: dict):
        try:
            print("[TELEMETRY] Compiling metadata payload...")
            creds = self.auth.get_credentials()
            service = build('sheets', 'v4', credentials=creds)

            # Format: [Timestamp, MachineID, Name, Email, Designation, Target Folder, Verified Count, Verified Amt, Flagged/Failed]
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            row_data = [
                timestamp,
                profile.get('machine_id', 'UNKNOWN_ID'),
                f"{profile.get('first_name', '')} {profile.get('last_name', '')}",
                profile.get('email', ''),
                profile.get('designation', ''),
                folder_name,
                stats.get('verified', 0),
                stats.get('total_amt', 0.0),
                stats.get('manual', 0) + stats.get('failed', 0)
            ]

            body = {'values': [row_data]}
            
            # Append the row to the bottom of the designated sheet
            service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A1",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()
            
            print(f"[TELEMETRY] ✅ Successfully synced session data to Master Ledger.")
            
        except Exception as e:
            print(f"[TELEMETRY ERROR] Network/API failure during sync: {e}")