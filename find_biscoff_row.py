#!/usr/bin/env python3
"""Find the biscoff row in the sheet"""
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

SHEET_ID = "1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno"

credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)

http = httplib2.Http(proxy_info=None)
authorized_http = AuthorizedHttp(credentials, http=http)
sheets_service = build('sheets', 'v4', http=authorized_http)

# Check multiple tabs
tabs_to_check = ["1-24", "11-30"]

for tab_name in tabs_to_check:
    try:
        print(f"\n{'='*80}")
        print(f"TAB: {tab_name}")
        print(f"{'='*80}")
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=f"'{tab_name}'!A:A"
        ).execute()
        
        values = result.get('values', [])
        print(f"\nCookie names in column A (total rows: {len(values)}):\n")
        for idx, row in enumerate(values[2:20], start=3):  # Skip header rows
            if row and len(row) > 0:
                cookie_name = row[0]
                if 'biscoff' in cookie_name.lower() or 'brookie' in cookie_name.lower() or 'brownie' in cookie_name.lower() or 'cheesecake' in cookie_name.lower():
                    print(f"Row {idx}: {cookie_name} [MATCH]")
                else:
                    print(f"Row {idx}: {cookie_name}")
    except Exception as e:
        print(f"ERROR reading {tab_name}: {e}")
