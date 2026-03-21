#!/usr/bin/env python3
"""
Fix Plaza Del Sol Cookies & Cream value for January 24th
API shows 14, sheet shows 1 - correcting to 14
"""

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Configuration
JANUARY_SHEET_ID = "1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Get yesterday's date (January 24, 2026)
tz = ZoneInfo("America/Puerto_Rico")
today = datetime.now(tz)
yesterday = today - timedelta(days=1)
TAB_NAME = f"{yesterday.month}-{yesterday.day}"  # "1-24"

# Correct value from API
CORRECT_VALUE = 14

print("="*80)
print(f"FIXING PLAZA DEL SOL COOKIES & CREAM FOR {yesterday.strftime('%Y-%m-%d')} ({TAB_NAME})")
print("="*80)
print(f"Correct value: {CORRECT_VALUE}")
print()

def get_sheet_service():
    """Get Google Sheets service"""
    creds = service_account.Credentials.from_service_account_file(
        'service-account-key.json',
        scopes=SCOPES
    )
    return build('sheets', 'v4', credentials=creds)

def column_to_letter(n):
    """Convert column index to letter (0 -> A, 1 -> B, etc.)"""
    result = ""
    while n >= 0:
        result = chr(65 + (n % 26)) + result
        n = n // 26 - 1
    return result

def main():
    service = get_sheet_service()
    
    # Read sheet to find cookie row and location column
    range_name = f"{TAB_NAME}!A:ZZ"
    result = service.spreadsheets().values().get(
        spreadsheetId=JANUARY_SHEET_ID,
        range=range_name
    ).execute()
    
    values = result.get('values', [])
    if not values:
        print(f"ERROR: No data found in tab {TAB_NAME}")
        return
    
    # Find location row and headers
    location_row = values[0] if len(values) > 0 else []
    headers = values[1] if len(values) > 1 else []
    
    # Find Plaza Del Sol column (look for "Live Sales Data" header with "Plaza del Sol" in location row)
    plaza_col_idx = None
    for i, header in enumerate(headers):
        if i < len(location_row):
            location_name = str(location_row[i]).strip()
            header_str = str(header).strip()
            
            if ("plaza del sol" in location_name.lower() or "plazasol" in location_name.lower()) and \
               "Live Sales Data" in header_str and "Do Not Touch" in header_str:
                plaza_col_idx = i
                print(f"Found Plaza Del Sol column: {column_to_letter(i)} (index {i})")
                print(f"  Location: {location_name}")
                print(f"  Header: {header_str}")
                break
    
    if plaza_col_idx is None:
        print("ERROR: Could not find Plaza Del Sol column")
        return
    
    # Find Cookies & Cream row
    cookies_cream_row = None
    for i, row in enumerate(values):
        if i < 2:  # Skip header rows
            continue
        cookie_cell = row[0] if len(row) > 0 else ""
        cookie_str = str(cookie_cell).strip()
        
        if 'cookies' in cookie_str.lower() and 'cream' in cookie_str.lower():
            cookies_cream_row = i + 1  # Convert to 1-based
            print(f"Found Cookies & Cream row: {cookies_cream_row}")
            print(f"  Cookie name: {cookie_str}")
            break
    
    if cookies_cream_row is None:
        print("ERROR: Could not find Cookies & Cream row")
        return
    
    # Get current value
    cell_range = f"{TAB_NAME}!{column_to_letter(plaza_col_idx)}{cookies_cream_row}"
    current_result = service.spreadsheets().values().get(
        spreadsheetId=JANUARY_SHEET_ID,
        range=cell_range
    ).execute()
    
    current_value = 0
    if current_result.get('values') and current_result['values'][0]:
        try:
            current_value = float(current_result['values'][0][0])
        except (ValueError, TypeError):
            current_value = 0
    
    print(f"\nCurrent sheet value: {current_value}")
    print(f"Correct API value: {CORRECT_VALUE}")
    
    if current_value == CORRECT_VALUE:
        print("\nValue is already correct! No update needed.")
        return
    
    # Get sheet tab ID
    sheet_metadata = service.spreadsheets().get(spreadsheetId=JANUARY_SHEET_ID).execute()
    sheet_tab_id = None
    for sheet_info in sheet_metadata.get('sheets', []):
        if sheet_info['properties']['title'] == TAB_NAME:
            sheet_tab_id = sheet_info['properties']['sheetId']
            break
    
    if sheet_tab_id is None:
        print(f"ERROR: Could not find sheet tab ID for {TAB_NAME}")
        return
    
    # Update the value using batchUpdate
    batch_request = {
        'requests': [{
            'updateCells': {
                'range': {
                    'sheetId': sheet_tab_id,
                    'startRowIndex': cookies_cream_row - 1,  # Convert to 0-based
                    'endRowIndex': cookies_cream_row,
                    'startColumnIndex': plaza_col_idx,
                    'endColumnIndex': plaza_col_idx + 1
                },
                'rows': [{
                    'values': [{
                        'userEnteredValue': {'numberValue': float(CORRECT_VALUE)}
                    }]
                }],
                'fields': 'userEnteredValue'
            }
        }]
    }
    
    print(f"\nUpdating cell {cell_range} to {CORRECT_VALUE}...")
    result = service.spreadsheets().batchUpdate(
        spreadsheetId=JANUARY_SHEET_ID,
        body=batch_request
    ).execute()
    
    print(f"[OK] Successfully updated!")
    print(f"   Cell: {cell_range}")
    print(f"   Old value: {current_value}")
    print(f"   New value: {CORRECT_VALUE}")

if __name__ == "__main__":
    main()
