#!/usr/bin/env python3
"""
Final fix for January 20th values based on user feedback
"""

import sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Configuration
JANUARY_SHEET_ID = "1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE"
SERVICE_ACCOUNT_FILE = "service-account-key.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
TAB_NAME = "1-20"

# Fix encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def column_to_letter(column_index):
    """Convert a 0-indexed column number to a Google Sheet column letter."""
    result = ""
    while column_index >= 0:
        result = chr(65 + (column_index % 26)) + result
        column_index = column_index // 26 - 1
    return result

def get_sheet_service():
    """Authenticates and returns the Google Sheets service."""
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)

def get_sheet_info(service, sheet_id, tab_name):
    """Get sheet title, tab ID, location row, and headers."""
    sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheets = sheet_metadata.get('sheets', [])
    
    tab_id = None
    for sheet in sheets:
        if sheet['properties']['title'] == tab_name:
            tab_id = sheet['properties']['sheetId']
            break
    
    if tab_id is None:
        raise ValueError(f"Tab '{tab_name}' not found in sheet.")

    range_name = f"{tab_name}!A1:BZ2"
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=range_name
    ).execute()
    values = result.get('values', [])
    
    if len(values) < 2:
        raise ValueError("Not enough rows to get location and headers.")
    
    location_row = values[0]
    headers = values[1]
    
    return tab_id, location_row, headers

def get_cookie_row(service, sheet_id, tab_name, cookie_name_to_find):
    """Finds the row number for a given cookie name."""
    range_name = f"{tab_name}!A:A"
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=range_name
    ).execute()
    values = result.get('values', [])
    
    for i, row in enumerate(values):
        if row and row[0].strip() == cookie_name_to_find:
            return i + 1
    return None

def get_location_column(location_row, headers, target_location):
    """Finds the column index for a given location's 'Live Sales Data (Do Not Touch)' column."""
    for i, header in enumerate(headers):
        if "Live Sales Data" in str(header) and "Do Not Touch" in str(header):
            if i < len(location_row) and str(location_row[i]).strip() == target_location:
                return i
    return None

def main():
    print("="*80)
    print("FINAL FIX FOR JANUARY 20TH VALUES")
    print("="*80)
    
    # Based on user feedback, these are the correct values:
    target_values = {
        "Cookies & Cream": {
            "Plaza del Sol": 11,
            "Plaza Carolina": 7,
            "Plaza Las Americas": 22,
        },
        "Chocolate Chip Nutella": {
            "Plaza Las Americas": 21,
        }
    }
    
    service = get_sheet_service()
    tab_id, location_row, headers = get_sheet_info(service, JANUARY_SHEET_ID, TAB_NAME)
    
    # Find cookie rows
    cookies_cream_row = get_cookie_row(service, JANUARY_SHEET_ID, TAB_NAME, "C - Cookies & Cream")
    chocolate_chip_nutella_row = get_cookie_row(service, JANUARY_SHEET_ID, TAB_NAME, "A - Chocolate Chip Nutella")
    
    if cookies_cream_row is None:
        print("ERROR: 'C - Cookies & Cream' row not found.")
        return
    if chocolate_chip_nutella_row is None:
        print("ERROR: 'A - Chocolate Chip Nutella' row not found.")
        return
    
    print(f"\nFound Cookies & Cream at row {cookies_cream_row}")
    print(f"Found Chocolate Chip Nutella at row {chocolate_chip_nutella_row}")
    
    # Build update requests
    requests = []
    
    # Update Cookies & Cream
    for location, value in target_values["Cookies & Cream"].items():
        col_idx = get_location_column(location_row, headers, location)
        if col_idx is None:
            print(f"  WARNING: Column not found for {location}")
            continue
        
        print(f"  {location} - Cookies & Cream: {value} (column {column_to_letter(col_idx)})")
        requests.append({
            'updateCells': {
                'range': {
                    'sheetId': tab_id,
                    'startRowIndex': cookies_cream_row - 1,
                    'endRowIndex': cookies_cream_row,
                    'startColumnIndex': col_idx,
                    'endColumnIndex': col_idx + 1
                },
                'rows': [{
                    'values': [{
                        'userEnteredValue': {'numberValue': float(value)}
                    }]
                }],
                'fields': 'userEnteredValue'
            }
        })
    
    # Update Chocolate Chip Nutella
    for location, value in target_values["Chocolate Chip Nutella"].items():
        col_idx = get_location_column(location_row, headers, location)
        if col_idx is None:
            print(f"  WARNING: Column not found for {location}")
            continue
        
        print(f"  {location} - Chocolate Chip Nutella: {value} (column {column_to_letter(col_idx)})")
        requests.append({
            'updateCells': {
                'range': {
                    'sheetId': tab_id,
                    'startRowIndex': chocolate_chip_nutella_row - 1,
                    'endRowIndex': chocolate_chip_nutella_row,
                    'startColumnIndex': col_idx,
                    'endColumnIndex': col_idx + 1
                },
                'rows': [{
                    'values': [{
                        'userEnteredValue': {'numberValue': float(value)}
                    }]
                }],
                'fields': 'userEnteredValue'
            }
        })
    
    if requests:
        print(f"\nUpdating {len(requests)} cells...")
        body = {'requests': requests}
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=JANUARY_SHEET_ID,
            body=body
        ).execute()
        print(f"✅ Successfully updated {len(requests)} cells!")
        
        # Verify updates
        print("\nVerifying updates...")
        for cookie_name, locations in target_values.items():
            row = cookies_cream_row if cookie_name == "Cookies & Cream" else chocolate_chip_nutella_row
            for location, expected_value in locations.items():
                col_idx = get_location_column(location_row, headers, location)
                if col_idx is not None:
                    cell_range = f"{TAB_NAME}!{column_to_letter(col_idx)}{row}"
                    result = service.spreadsheets().values().get(
                        spreadsheetId=JANUARY_SHEET_ID, range=cell_range
                    ).execute()
                    current_value = result.get('values', [['0']])[0][0]
                    status = "OK" if str(current_value) == str(expected_value) else "MISMATCH"
                    print(f"  {location} - {cookie_name}: {current_value} (expected: {expected_value}) [{status}]")
    else:
        print("No updates to make.")

if __name__ == "__main__":
    main()
