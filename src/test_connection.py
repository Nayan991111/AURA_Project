import os.path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


SPREADSHEET_ID = '1UWcUhHrJx6jokEaSOd-lVthecqvnLpiSKuFX2p5zuiQ' 
# Reading from A1 to D1 to test connection and permissions. Adjust as needed for your sheet structure.
RANGE_NAME = 'Sheet1!A1:D1' 
# ---------------------

SCOPES = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/spreadsheets']
TOKEN_PATH = 'assets/config/token.json'

def fetch_data():
    creds = None
    # 1. Load the token just saved
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    else:
        print(f"[ERROR] Token file not found at {TOKEN_PATH}. Run auth_manager.py first.")
        return

    try:
        # 2. Build the Sheets API service
        service = build('sheets', 'v4', credentials=creds)

        # 3. Call the Sheets API
        print(f"[INFO] Connecting to Sheet ID: {SPREADSHEET_ID}...")
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
        values = result.get('values', [])

        # 4. Print Results
        if not values:
            print('[INFO] No data found.')
        else:
            print("\n--- DATA RETRIEVED FROM GOOGLE SHEETS ---")
            for row in values:
                print(row)
            print("-----------------------------------------")

    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")

if __name__ == '__main__':
    fetch_data()