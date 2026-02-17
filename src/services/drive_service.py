import os
import io
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

class DriveService:
    """
    GOOGLE DRIVE SERVICE v4.1 (Stable)
    Includes: Auth, recursive listing, memory download, and metadata fetching.
    """
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    # Path relative to project root
    BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..', '..'))
    
    CREDENTIALS_PATH = os.path.join(PROJECT_ROOT, 'assets', 'config', 'credentials.json')
    TOKEN_PATH = os.path.join(PROJECT_ROOT, 'assets', 'config', 'token.json')

    def __init__(self):
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None
        if os.path.exists(self.TOKEN_PATH):
            with open(self.TOKEN_PATH, 'rb') as token:
                try:
                    creds = pickle.load(token)
                except:
                    creds = None # Handle corrupt token
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except:
                    creds = None
            
            if not creds:
                if not os.path.exists(self.CREDENTIALS_PATH):
                    raise FileNotFoundError(f"❌ MISSING: {self.CREDENTIALS_PATH}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.CREDENTIALS_PATH, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the new token
            os.makedirs(os.path.dirname(self.TOKEN_PATH), exist_ok=True)
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
        """
        [NEW] Fetches the name of the folder (e.g., 'Arundhati Donation').
        Critical for the AuditManager logging.
        """
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
                    # Recursive dive
                    files_found.extend(self.list_files_recursive(item['id']))
                elif 'image' in item['mimeType'] or 'pdf' in item['mimeType']:
                    files_found.append(item)
                    
        except Exception as e:
            print(f"   [WARN] Error scanning folder {folder_id}: {e}")
            
        return files_found

    def download_file_to_memory(self, file_id):
        """Downloads file bytes directly to RAM"""
        request = self.service.files().get_media(fileId=file_id)
        file_stream = io.BytesIO()
        downloader = request.execute()
        file_stream.write(downloader)
        file_stream.seek(0)
        return file_stream