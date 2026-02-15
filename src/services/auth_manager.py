import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

class AuthManager:
    """
    Handles secure authentication with Google Services.
    Follows the 'Local-First' architecture by storing tokens locally as JSON.
    """
    
    # Scopes: Read Drive files, Read/Write Sheets
    SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/spreadsheets'
    ]

    def __init__(self, base_path=None):
        # Allow dynamic path resolution
        if base_path is None:
            # considering running from root, so assets is at ./assets
            base_path = os.getcwd()
            
        # Define paths for credentials and token
        self.creds_path = os.path.join(base_path, 'assets', 'config', 'credentials.json')
        self.token_path = os.path.join(base_path, 'assets', 'config', 'token.json')
        self.creds = None

    def get_credentials(self):
        """
        Retrieves valid user credentials from local storage or initiates
        the OAuth2 login flow.
        """
        # 1. Check for existing token.json
        if os.path.exists(self.token_path):
            try:
                # Load credentials from JSON file instead of Pickle
                self.creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
            except Exception as e:
                print(f"[ERROR] Corrupt token found: {e}")
                self.creds = None

        # 2. Refresh or Login if needed
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                print("[INFO] Token expired. Refreshing...")
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    print(f"[ERROR] Refresh failed: {e}. Re-authenticating.")
                    self._perform_login()
            else:
                print("[INFO] No valid session. Initiating Login...")
                self._perform_login()

        return self.creds

    def _perform_login(self):
        """
        Launches the browser for the user to sign in.
        """
        if not os.path.exists(self.creds_path):
            raise FileNotFoundError(f"CRITICAL: 'credentials.json' not found at {self.creds_path}. "
                                    "Please download it from Google Cloud Console.")
        
        flow = InstalledAppFlow.from_client_secrets_file(
            self.creds_path, self.SCOPES
        )
        
        # Opens a local server for the callback
        # We use port 0 to let the OS pick a free port, or you can specify 63686 if needed
        self.creds = flow.run_local_server(port=0)
        
        # Save the token as JSON (Text) instead of Pickle (Binary)
        print(f"[SUCCESS] Authenticated. Saving token to {self.token_path}")
        with open(self.token_path, 'w') as token:
            token.write(self.creds.to_json())

if __name__ == "__main__":
    # Day 1 Sanity Check
    print("--- AURA AUTH SYSTEM DIAGNOSTIC ---")
    auth = AuthManager()
    try:
        creds = auth.get_credentials()
        print(f"[PASS] Authentication Successful.")
        print(f"[INFO] Access Token Scope: {creds.scopes}")
    except Exception as e:
        print(f"[FAIL] Authentication Error: {e}")