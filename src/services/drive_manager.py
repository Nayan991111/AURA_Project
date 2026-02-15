import sys
import os
import re
from typing import List, Dict, Optional, Any

# PATH FIX: Add project root to python path to allow direct execution
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path: sys.path.append(project_root)

from googleapiclient.discovery import build
from src.services.auth_manager import AuthManager

class DriveManager:
    """
    Handles all interactions with Google Drive API v3.
    Responsibility: Crawling, Metadata Extraction, and File Listing.
    Standard: Universal Compatibility (iOS/Android/Web).
    """
    
    # MIME Types we care about for the Audit
    # EXPANDED: Now includes Apple HEIC, Android HEIF, and WebP
    TARGET_MIMES = [
        'image/jpeg', 
        'image/png', 
        'application/pdf',
        'image/heif',
        'image/heic',
        'image/webp'
    ]
    
    FOLDER_MIME = 'application/vnd.google-apps.folder'

    def __init__(self):
        self.auth = AuthManager()
        self.creds = self.auth.get_credentials()
        
        if not self.creds:
            raise PermissionError("[CRITICAL] Authentication failed. Cannot initialize DriveManager.")
            
        self.service = build('drive', 'v3', credentials=self.creds)

    def extract_folder_id(self, url: str) -> Optional[str]:
        """
        Parses a raw URL string to extract the Google Drive Folder ID.
        Supports standard URL formats, mobile sharing links, and raw IDs.
        """
        # Regex for standard folder links and mobile links
        patterns = [
            r'folders\/([a-zA-Z0-9-_]+)',  # Standard /folders/ID
            r'id=([a-zA-Z0-9-_]+)',         # Parameter based ?id=ID
            r'drive\.google\.com\/.*\/([a-zA-Z0-9-_]+)$' # Catch-all end of URL
        ]
        
        for p in patterns:
            match = re.search(p, url)
            if match:
                return match.group(1)
        
        # Fallback: Assume the user pasted the ID directly if it looks like one
        if 'http' not in url and len(url) > 15:
            return url.strip()
            
        return None

    def get_folder_metadata(self, folder_id: str) -> Dict[str, Any]:
        """
        Fetches the Name and Owner of the root folder.
        Crucial for auto-attributing the 'Intern Name'.
        """
        try:
            file = self.service.files().get(
                fileId=folder_id,
                fields='id, name, owners(displayName, emailAddress)'
            ).execute()
            
            # Extract primary owner
            owners = file.get('owners', [])
            owner_name = owners[0]['displayName'] if owners else "Unknown"
            
            return {
                'folder_name': file.get('name'),
                'owner_name': owner_name,
                'folder_id': file.get('id')
            }
        except Exception as e:
            print(f"[ERROR] Could not fetch folder metadata: {e}")
            return {'folder_name': 'Unknown', 'owner_name': 'Unknown', 'folder_id': folder_id}

    def list_files(self, folder_id: str, recursive: bool = True) -> List[Dict[str, Any]]:
        """
        Recursively lists all valid image/pdf files in the folder.
        Returns a flat list of file objects.
        """
        files_found = []
        page_token = None
        
        # Query: Inside this folder AND not in trash
        query = f"'{folder_id}' in parents and trashed = false"

        try:
            while True:
                response = self.service.files().list(
                    q=query,
                    spaces='drive',
                    # Requesting mimeType explicitly to filter
                    fields='nextPageToken, files(id, name, mimeType)',
                    pageToken=page_token
                ).execute()

                for file in response.get('files', []):
                    mime = file.get('mimeType')
                    name = file.get('name')
                    file_id = file.get('id')

                    # CASE 1: It's a Folder (Recurse)
                    if mime == self.FOLDER_MIME and recursive:
                        print(f"   [+] Entering Sub-folder: {name}")
                        # Recursive call
                        sub_files = self.list_files(file_id, recursive=True)
                        files_found.extend(sub_files)

                    # CASE 2: It's a Target File (Collect)
                    elif mime in self.TARGET_MIMES:
                        files_found.append({
                            'id': file_id,
                            'name': name,
                            'mime': mime
                        })
                    
                    # CASE 3: Debugging (Log skipped files to identify missing types)
                    else:
                        print(f"   [DEBUG] Skipped File: {name} (Type: {mime})")
                
                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
                    
        except Exception as e:
            print(f"[ERROR] Listing files in {folder_id}: {e}")
            
        return files_found

# Allow running this file directly for quick validation
if __name__ == "__main__":
    print("--- DriveManager v1.2 (iOS/Android Enhanced) ---")
    dm = DriveManager()
    
    # TEST: Ask user for a link
    test_link = input("Enter a Google Drive Folder Link to test: ")
    f_id = dm.extract_folder_id(test_link)
    
    if f_id:
        print(f"[1] ID Extracted: {f_id}")
        meta = dm.get_folder_metadata(f_id)
        print(f"[2] Metadata: {meta}")
        
        print(f"[3] Scanning files (Recursive)...")
        files = dm.list_files(f_id)
        print(f"\n[SUMMARY] Found {len(files)} VALID files.")
        
        print("\n--- Manifest ---")
        for f in files: 
            print(f" - {f['name']} ({f['mime']})")
    else:
        print("[FAIL] Invalid Link")