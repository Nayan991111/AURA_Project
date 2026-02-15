import os
import io
import pickle
import re
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

class DriveService:
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(self):
        self.creds = None
        self.service = None
        self._authenticate()

    def _authenticate(self):
        # M4 Compliant Token Storage (Hidden in Home Dir)
        token_dir = os.path.expanduser("~/.aura_tokens")
        os.makedirs(token_dir, exist_ok=True)
        token_path = os.path.join(token_dir, 'token.pickle')
        creds_path = 'credentials.json'

        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                self.creds = pickle.load(token)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(creds_path):
                    raise FileNotFoundError(f"Missing {creds_path}")
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open(token_path, 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('drive', 'v3', credentials=self.creds)

    def extract_folder_id(self, url: str) -> str:
        patterns = [r'folders\/([a-zA-Z0-9\-_]+)', r'id=([a-zA-Z0-9\-_]+)', r'^([a-zA-Z0-9\-_]+)$']
        for p in patterns:
            match = re.search(p, url)
            if match: return match.group(1)
        raise ValueError("Invalid Drive Link")

    def get_folder_name(self, folder_id):
        try:
            res = self.service.files().get(fileId=folder_id, fields="name").execute()
            return res.get('name', 'Unknown Folder')
        except: return "Unknown Folder"

    def list_files_recursive(self, folder_id):
        files_found = []
        query = f"'{folder_id}' in parents and trashed = false"
        page_token = None
        
        while True:
            results = self.service.files().list(
                q=query, fields="nextPageToken, files(id, name, mimeType)", pageToken=page_token
            ).execute()
            
            for item in results.get('files', []):
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    files_found.extend(self.list_files_recursive(item['id']))
                elif any(x in item['mimeType'] for x in ['image/', 'pdf']):
                    files_found.append(item)
            
            page_token = results.get('nextPageToken')
            if not page_token: break
                
        return files_found

    def download_file_to_memory(self, file_id):
        """Downloads chunks to RAM."""
        request = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return fh