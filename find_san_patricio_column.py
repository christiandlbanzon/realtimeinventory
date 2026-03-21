#!/usr/bin/env python3
"""
Find the correct San Patricio Live Sales Data column
"""
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

SHEET_ID = "1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE"
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)

http = httplib2.Http(proxy_info=None)
authorized_http = AuthorizedHttp(credentials, http=http)
sheets_service = build('sheets', 'v4', http=authorized_http)

tab_name = "1-26"

def column_to_letter(n):
    """Convert column number to letter"""
    result = ""
    while n >= 0:
        result = chr(65 + (n % 26)) + result
        n = n // 26 - 1
    return result

print("="*80)
print(f"FINDING SAN PATRICIO LIVE SALES DATA COLUMN IN TAB '{tab_name}'")
print("="*80)
print()

# Read rows 1 and 2 (location row and headers)
try:
    range_name = f"'{tab_name}'!1:2"
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=range_name
    ).execute()
    values = result.get('values', [])
    
    if len(values) >= 2:
        location_row = values[0] if len(values) > 0 else []
        headers = values[1] if len(values) > 1 else []
        
        print("Searching for 'San Patricio' in location row and 'Live Sales Data' in headers...")
        print()
        
        san_patricio_cols = []
        for i in range(min(len(location_row), len(headers))):
            location = str(location_row[i]) if i < len(location_row) else ""
            header = str(headers[i]) if i < len(headers) else ""
            
            if 'san patricio' in location.lower() and 'live sales data' in header.lower() and 'do not touch' in header.lower():
                col_letter = column_to_letter(i)
                san_patricio_cols.append((i, col_letter, location, header))
                print(f"  [FOUND] Column {col_letter} (index {i}):")
                print(f"    Location: {location}")
                print(f"    Header: {header}")
        
        if not san_patricio_cols:
            print("  No exact match found. Checking all columns with 'San Patricio'...")
            for i in range(min(len(location_row), len(headers))):
                location = str(location_row[i]) if i < len(location_row) else ""
                header = str(headers[i]) if i < len(headers) else ""
                
                if 'san patricio' in location.lower():
                    col_letter = column_to_letter(i)
                    print(f"  Column {col_letter} (index {i}):")
                    print(f"    Location: {location}")
                    print(f"    Header: {header}")
                    if 'live sales' in header.lower():
                        print(f"    *** This might be the Live Sales Data column ***")
        
        # Check what's in F8 and surrounding San Patricio columns
        print()
        print("="*80)
        print("VALUES IN ROW 8 FOR SAN PATRICIO COLUMNS:")
        print("="*80)
        
        # Read row 8
        row8_range = f"'{tab_name}'!8:8"
        row8_result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=row8_range
        ).execute()
        row8_values = row8_result.get('values', [])
        
        if row8_values and len(row8_values) > 0:
            row8 = row8_values[0]
            for i in range(min(20, len(row8))):
                col_letter = column_to_letter(i)
                value = row8[i] if i < len(row8) else ""
                location = str(location_row[i]) if i < len(location_row) else ""
                header = str(headers[i]) if i < len(headers) else ""
                
                if 'san patricio' in location.lower():
                    print(f"  {col_letter}8 (index {i}): {value}")
                    print(f"    Location: {location}")
                    print(f"    Header: {header}")
                    print()
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
