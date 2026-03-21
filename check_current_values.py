#!/usr/bin/env python3
"""
Check current values in the sheet
"""

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = "service-account-key.json"
JANUARY_SHEET_ID = "1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE"

def check_values():
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=creds)
    
    tab_name = "1-20"
    
    print("="*80)
    print("CURRENT VALUES IN SHEET")
    print("="*80)
    
    # Check Cookies & Cream (row 5) and Chocolate Chip Nutella (row 3)
    cells_to_check = {
        "Cookies & Cream - Plaza del Sol": "T5",
        "Cookies & Cream - Plaza Las Americas": "BJ5",
        "Cookies & Cream - Old San Juan": "BU5",
        "Cookies & Cream - Plaza Carolina": "AV5",
        "Chocolate Chip Nutella - Plaza Las Americas": "BJ3",
    }
    
    for name, cell in cells_to_check.items():
        result = service.spreadsheets().values().get(
            spreadsheetId=JANUARY_SHEET_ID,
            range=f'{tab_name}!{cell}'
        ).execute()
        
        values = result.get('values', [])
        value = values[0][0] if values and len(values[0]) > 0 else "0"
        print(f"  {name} ({cell}): {value}")

if __name__ == "__main__":
    check_values()
