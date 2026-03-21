#!/usr/bin/env python3
"""Test access to February Google Sheet and do a sample update"""

import os
import sys
from datetime import datetime

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'service-account-key.json'

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

SHEET_ID = "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4"
GID = "859424086"

print("="*80)
print("TESTING GOOGLE SHEET ACCESS")
print("="*80)
print(f"\nSheet ID: {SHEET_ID}")
print(f"GID: {GID}")
print(f"URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid={GID}")
print()

# Authenticate
print("[1/4] Authenticating...")
try:
    credentials = service_account.Credentials.from_service_account_file(
        'service-account-key.json',
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    http = httplib2.Http(proxy_info=None, timeout=60)
    authorized_http = AuthorizedHttp(credentials, http=http)
    sheets = build('sheets', 'v4', http=authorized_http)
    print(f"  OK: Authenticated as {credentials.service_account_email}")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# Get sheet metadata
print("\n[2/4] Getting sheet metadata...")
try:
    spreadsheet = sheets.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    print(f"  Title: {spreadsheet.get('properties', {}).get('title', 'N/A')}")
    
    sheets_list = spreadsheet.get('sheets', [])
    print(f"  Found {len(sheets_list)} sheet(s):")
    for sheet in sheets_list:
        props = sheet.get('properties', {})
        sheet_id = props.get('sheetId')
        title = props.get('title', 'N/A')
        if sheet_id == int(GID):
            print(f"    -> {title} (GID: {sheet_id}) - THIS IS THE TARGET SHEET")
        else:
            print(f"    - {title} (GID: {sheet_id})")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# Read a sample cell
print("\n[3/4] Reading sample data...")
try:
    # Use the actual tab name "2-1" (found from metadata)
    tab_name = "2-1"
    # Read cell A1 to verify read access
    range_name = f"{tab_name}!A1"
    result = sheets.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=range_name
    ).execute()
    
    values = result.get('values', [])
    if values:
        print(f"  Cell A1: {values[0][0] if values[0] else 'Empty'}")
    else:
        print(f"  Cell A1: Empty")
    
    # Read a few more cells to see structure
    range_name = f"{tab_name}!A1:C3"
    result = sheets.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=range_name
    ).execute()
    
    values = result.get('values', [])
    print(f"\n  Sample data (A1:C3):")
    for i, row in enumerate(values[:3], 1):
        print(f"    Row {i}: {row}")
        
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Write a test value
print("\n[4/4] Writing test value...")
try:
    # Find an empty cell or use a test cell (like Z100 which should be empty)
    test_cell = "Z100"
    test_value = f"Test update at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    print(f"  Writing to cell {test_cell}: {test_value}")
    
    range_name = f"{tab_name}!{test_cell}"
    body = {
        'values': [[test_value]]
    }
    
    result = sheets.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range=range_name,
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()
    
    updated_cells = result.get('updatedCells', 0)
    print(f"  OK: Updated {updated_cells} cell(s)")
    
    # Verify the write
    result = sheets.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=range_name
    ).execute()
    
    values = result.get('values', [])
    if values and values[0]:
        print(f"  Verified: Cell {test_cell} now contains: {values[0][0]}")
    
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()
    
    if "permission" in str(e).lower() or "access" in str(e).lower():
        print("\n  PERMISSION ISSUE:")
        print(f"  The service account needs 'Editor' access to the sheet.")
        print(f"  Share the sheet with: {credentials.service_account_email}")
        print(f"  Grant 'Editor' permission")
    sys.exit(1)

print("\n" + "="*80)
print("TEST COMPLETE!")
print("="*80)
print(f"\nOK: Can read from sheet")
print(f"OK: Can write to sheet")
print(f"\nThe Cloud Run Job should be able to update this sheet successfully!")
print(f"\nView the test value:")
print(f"  https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid={GID}#gid={GID}")
print(f"  (Check cell Z100)")
