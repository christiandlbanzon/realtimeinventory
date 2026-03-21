#!/usr/bin/env python3
"""Check if the sheet was actually updated by the Cloud Run Job"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'service-account-key.json'

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

SHEET_ID = "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4"

print("="*80)
print("CHECKING IF SHEET WAS UPDATED")
print("="*80)

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
sheets = build('sheets', 'v4', http=authorized_http)

# Get current date in Puerto Rico timezone (same as script)
tz = ZoneInfo("America/Puerto_Rico")
now = datetime.now(tz)
current_month = now.month
current_day = now.day

print(f"\nCurrent date (Puerto Rico timezone): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"Month: {current_month}, Day: {current_day}")

# Determine expected tab name (same logic as script)
if current_month >= 2:  # February and onwards
    expected_tab = f"{current_month}-{current_day}"
    print(f"\nExpected tab name: '{expected_tab}'")
else:
    expected_tab = f"{current_month}-{current_day}"
    print(f"\nExpected tab name: '{expected_tab}'")

# Get all tabs
print(f"\n[1/3] Getting sheet tabs...")
try:
    spreadsheet = sheets.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    sheets_list = spreadsheet.get('sheets', [])
    
    print(f"  Found {len(sheets_list)} tab(s):")
    target_tab = None
    for sheet in sheets_list:
        props = sheet.get('properties', {})
        title = props.get('title', 'N/A')
        sheet_id = props.get('sheetId')
        print(f"    - '{title}' (GID: {sheet_id})")
        if title == expected_tab:
            target_tab = title
            print(f"      -> This is the target tab for today!")
    
    if not target_tab:
        print(f"\n  WARNING: Tab '{expected_tab}' not found!")
        print(f"  The script might be looking for a tab that doesn't exist yet.")
        print(f"  Available tabs: {[s.get('properties', {}).get('title') for s in sheets_list]}")
        
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# Check "Live Sales Data" columns (column F typically)
print(f"\n[2/3] Checking 'Live Sales Data' column in tab '{expected_tab}'...")
if target_tab:
    try:
        # Read column F (Live Sales Data) for a few cookie types
        # Based on the sheet structure, cookies start at row 3
        range_name = f"{target_tab}!F3:F20"  # Check rows 3-20 (cookie types A-N)
        
        result = sheets.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if values:
            print(f"  Found {len(values)} rows in 'Live Sales Data' column:")
            print(f"\n  Cookie Type | Live Sales Data")
            print(f"  {'-'*50}")
            
            cookie_types = ['A - Chocolate Chip Nutella', 'B - Signature Chocolate Chip', 
                          'C - Cookies & Cream', 'D - White Chocolate Macadamia',
                          'E - Strawberry Cheesecake', 'F - Brookie']
            
            for i, row in enumerate(values[:15], 0):
                cookie_name = cookie_types[i] if i < len(cookie_types) else f"Row {i+3}"
                sales_value = row[0] if row else "Empty"
                print(f"  {cookie_name[:30]:30} | {sales_value}")
            
            # Check if values are non-zero (indicating updates)
            non_zero_count = sum(1 for row in values if row and row[0] and str(row[0]).strip() and str(row[0]) != '0')
            print(f"\n  Non-zero values: {non_zero_count} out of {len(values)}")
            
            if non_zero_count > 0:
                print(f"  OK: Sheet appears to have sales data!")
            else:
                print(f"  WARNING: All values are zero or empty")
                print(f"  This could mean:")
                print(f"    1. No sales yet today")
                print(f"    2. The job hasn't updated this tab yet")
                print(f"    3. The job is updating a different tab")
        else:
            print(f"  No data found in range {range_name}")
            
    except Exception as e:
        print(f"  ERROR reading data: {e}")
        import traceback
        traceback.print_exc()

# Check when the sheet was last modified
print(f"\n[3/3] Checking sheet modification time...")
try:
    # Get spreadsheet metadata
    spreadsheet = sheets.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    # Note: Sheets API doesn't directly provide modification time
    # But we can check if our test value is still there
    test_range = "2-1!Z100"
    result = sheets.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=test_range
    ).execute()
    
    values = result.get('values', [])
    if values and values[0]:
        print(f"  Test value in Z100: {values[0][0]}")
        print(f"  (This confirms write access works)")
    
except Exception as e:
    print(f"  Could not check modification: {e}")

print("\n" + "="*80)
print("RECOMMENDATION")
print("="*80)
print(f"\nThe Cloud Run Job should update tab '{expected_tab}' every 5 minutes.")
print(f"\nTo verify updates:")
print(f"  1. Check Cloud Run Job logs for what it did")
print(f"  2. Check if tab '{expected_tab}' exists")
print(f"  3. Check 'Live Sales Data' columns in that tab")
print(f"\nView logs:")
print(f"  https://console.cloud.google.com/run/jobs/inventory-updater/executions?project=boxwood-chassis-332307")
