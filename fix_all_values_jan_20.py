#!/usr/bin/env python3
"""
Fix all incorrect values for January 20th
"""

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = "service-account-key.json"
JANUARY_SHEET_ID = "1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE"

def fix_all():
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=creds)
    
    tab_name = "1-20"
    sheet_id = 1311252812  # 1-20 tab ID
    
    # Correct values from Clover API report
    # Plaza Las Americas: Cookies & Cream = 22, Chocolate Chip Nutella = 21
    # Plaza del Sol: Cookies & Cream = 11
    # Old San Juan: Cookies & Cream = 57
    # Plaza Carolina: Cookies & Cream = 7
    
    updates = {
        "BJ5": 22,   # Plaza Las Americas - Cookies & Cream
        "BJ3": 21,   # Plaza Las Americas - Chocolate Chip Nutella
        "T5": 11,    # Plaza del Sol - Cookies & Cream
        "BU5": 57,   # Old San Juan - Cookies & Cream
        "AV5": 7,    # Plaza Carolina - Cookies & Cream
    }
    
    print("="*80)
    print("FIXING ALL VALUES FOR JANUARY 20TH")
    print("="*80)
    
    def col_to_index(col_str):
        """Convert column letter to 0-based index"""
        result = 0
        for char in col_str:
            if char.isalpha():
                result = result * 26 + (ord(char.upper()) - ord('A') + 1)
        return result - 1
    
    def row_to_index(row_str):
        """Convert row number to 0-based index"""
        return int(row_str) - 1
    
    requests = []
    for cell, value in updates.items():
        col_letter = ''.join(c for c in cell if c.isalpha())
        row_num = ''.join(c for c in cell if c.isdigit())
        col_idx = col_to_index(col_letter)
        row_idx = row_to_index(row_num)
        
        requests.append({
            'updateCells': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': row_idx,
                    'endRowIndex': row_idx + 1,
                    'startColumnIndex': col_idx,
                    'endColumnIndex': col_idx + 1,
                },
                'rows': [{
                    'values': [{
                        'userEnteredValue': {'numberValue': value}
                    }]
                }],
                'fields': 'userEnteredValue'
            }
        })
        print(f"  {cell}: {value}")
    
    body = {'requests': requests}
    
    print("\nExecuting batchUpdate...")
    result = service.spreadsheets().batchUpdate(
        spreadsheetId=JANUARY_SHEET_ID,
        body=body
    ).execute()
    
    print(f"Updated {len(result.get('replies', []))} cells")
    
    # Verify
    import time
    time.sleep(2)
    print("\nVerifying...")
    for cell, expected_value in updates.items():
        result = service.spreadsheets().values().get(
            spreadsheetId=JANUARY_SHEET_ID,
            range=f'{tab_name}!{cell}'
        ).execute()
        
        values = result.get('values', [])
        actual_value = values[0][0] if values and len(values[0]) > 0 else "0"
        status = "OK" if str(actual_value) == str(expected_value) else "MISMATCH"
        print(f"  {cell}: {actual_value} (expected: {expected_value}) [{status}]")

if __name__ == "__main__":
    import time
    fix_all()
