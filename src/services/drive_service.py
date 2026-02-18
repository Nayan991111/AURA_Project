import os
import io
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# [CRITICAL] Import the path handler for Freeze/Production compatibility
from src.utils.path_handler import resource_path

class DriveService:
    """
    GOOGLE DRIVE SERVICE v4.2 (Production Ready)
    Includes: Hybrid Path Resolution (Dev/Frozen) and Persistent Token Storage.
    """
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    # 1. READ-ONLY ASSET (Credentials are bundled inside the App/Exe)
    # We use resource_path to find this file inside the _MEIPASS temp folder at runtime
    CREDENTIALS_PATH = resource_path(os.path.join('assets', 'config', 'credentials.json'))
    
    # 2. WRITABLE ASSET (Token must persist outside the frozen app)
    # We store the token in the User's Home Directory (~/.aura/) 
    # This prevents Permission Errors and ensures the login "sticks" after restart.
    TOKEN_PATH = os.path.join(os.path.expanduser("~"), '.aura', 'token.json')

    def __init__(self):
        # Ensure the hidden folder for the token exists in the user's home dir
        self._ensure_token_dir()
        
        # Verify Credentials Existence (Debug Step)
        if not os.path.exists(self.CREDENTIALS_PATH):
            print(f"[CRITICAL] Credentials NOT FOUND at: {self.CREDENTIALS_PATH}")
            
        self.service = self._authenticate()

    def _ensure_token_dir(self):
        """Creates the ~/.aura directory if it doesn't exist."""
        try:
            os.makedirs(os.path.dirname(self.TOKEN_PATH), exist_ok=True)
        except OSError:
            pass # Fallback if permissions are weird, though ~ should always be writable

    def _authenticate(self):
        creds = None
        # Try to load existing session
        if os.path.exists(self.TOKEN_PATH):
            try:
                with open(self.TOKEN_PATH, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                print(f"[AUTH] Token corrupted, resetting... ({e})")
                creds = None
        
        # Refresh or Create new session
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except:
                    creds = None
            
            if not creds:
                if not os.path.exists(self.CREDENTIALS_PATH):
                    raise FileNotFoundError(f"❌ CRITICAL: Missing credentials.json at {self.CREDENTIALS_PATH}")
                
                # Launch Browser Auth
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.CREDENTIALS_PATH, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save token to PERSISTENT path
            with open(self.TOKEN_PATH, 'wb') as token:
                pickle.dump(creds, token)

        return build('drive', 'v3', credentials=creds)

    def extract_folder_id(self, link: str) -> str:
        """Extracts ID from various Google Drive link formats"""
        if 'id=' in link:
            return link.split('id=')[-1].split('&')[0]
        elif '/folders/' in link:
            return link.split('/folders/')[-1].split('?')[0]
        return link 

    def get_folder_name(self, folder_id: str) -> str:
        """Fetches the name of the folder for logging."""
        try:
            file_metadata = self.service.files().get(fileId=folder_id, fields='name').execute()
            return file_metadata.get('name', 'Unknown Folder')
        except Exception as e:
            print(f"   [WARN] Could not fetch folder name: {e}")
            return "Target Folder"

    def list_files_recursive(self, folder_id):
        """Recursively finds all images in the folder."""
        files_found = []
        query = f"'{folder_id}' in parents and trashed = false"
        
        try:
            results = self.service.files().list(
                q=query, pageSize=100, fields="files(id, name, mimeType)").execute()
            items = results.get('files', [])

            for item in items:
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    files_found.extend(self.list_files_recursive(item['id']))
                elif any(ext in item['mimeType'] for ext in ['image', 'pdf']):
                    files_found.append(item)
                    
        except Exception as e:
            print(f"   [WARN] Error scanning folder {folder_id}: {e}")
            
        return files_found

    def download_file_to_memory(self, file_id):
        """Downloads file bytes directly to RAM (Stream)"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_stream = io.BytesIO()
            # execute() returns the raw bytes
            file_stream.write(request.execute())
            file_stream.seek(0)
            return file_stream
        except Exception as e:
            print(f"[ERROR] Download Failed for {file_id}: {e}")
            return None