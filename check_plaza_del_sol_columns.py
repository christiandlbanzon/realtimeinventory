#!/usr/bin/env python3
"""
Check all columns for Plaza Del Sol to verify Cookies & Cream values
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
    
    # Read sheet
    range_name = f"{TAB_NAME}!A:ZZ"
    result = service.spreadsheets().values().get(
        spreadsheetId=JANUARY_SHEET_ID,
        range=range_name
    ).execute()
    
    values = result.get('values', [])
    if not values:
        print(f"ERROR: No data found in tab {TAB_NAME}")
        return
    
    location_row = values[0] if len(values) > 0 else []
    headers = values[1] if len(values) > 1 else []
    
    # Find Cookies & Cream row
    cookies_cream_row = None
    for i, row in enumerate(values):
        if i < 2:
            continue
        cookie_cell = row[0] if len(row) > 0 else ""
        cookie_str = str(cookie_cell).strip()
        
        if 'cookies' in cookie_str.lower() and 'cream' in cookie_str.lower():
            cookies_cream_row = i + 1
            break
    
    if cookies_cream_row is None:
        print("ERROR: Could not find Cookies & Cream row")
        return
    
    print(f"Cookies & Cream row: {cookies_cream_row}")
    print()
    print("Checking all columns for Plaza Del Sol:")
    print("="*80)
    
    # Check all columns
    plaza_columns = []
    for i in range(min(len(location_row), len(headers), 100)):
        location_name = str(location_row[i]).strip() if i < len(location_row) else ""
        header = str(headers[i]).strip() if i < len(headers) else ""
        
        # Check if this column is related to Plaza Del Sol
        if any(keyword in location_name.lower() for keyword in ['plaza del sol', 'plazasol', 'plaza del']) or \
           any(keyword in header.lower() for keyword in ['plaza del sol', 'plazasol']):
            
            # Get the value at Cookies & Cream row
            value = 0
            if cookies_cream_row - 1 < len(values) and i < len(values[cookies_cream_row - 1]):
                value_str = values[cookies_cream_row - 1][i] if i < len(values[cookies_cream_row - 1]) else ""
                try:
                    value = float(value_str) if value_str else 0
                except (ValueError, TypeError):
                    value = 0
            
            col_letter = column_to_letter(i)
            print(f"Column {col_letter} (index {i}):")
            print(f"  Location: {location_name}")
            print(f"  Header: {header}")
            print(f"  Cookies & Cream value: {value}")
            print()
            
            if value > 0 or "Live Sales Data" in header:
                plaza_columns.append({
                    'col': col_letter,
                    'idx': i,
                    'location': location_name,
                    'header': header,
                    'value': value
                })
    
    print("="*80)
    print(f"Found {len(plaza_columns)} Plaza Del Sol-related columns:")
    for col_info in plaza_columns:
        print(f"  {col_info['col']}: {col_info['value']} ({col_info['location']} - {col_info['header']})")

if __name__ == "__main__":
    main()
