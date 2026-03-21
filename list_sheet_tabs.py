#!/usr/bin/env python3
"""List all tabs in the Google Sheet to find the correct format"""

import os
import sys

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

sheet_id = "1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno"

creds = Credentials.from_service_account_file(
    "service-account-key.json",
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

http = httplib2.Http(proxy_info=None)
authorized_http = AuthorizedHttp(creds, http=http)
service = build("sheets", "v4", http=authorized_http)

print("Fetching all sheet tabs...")
sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
sheet_titles = [sheet['properties']['title'] for sheet in sheet_metadata.get('sheets', [])]

print(f"\nTotal tabs: {len(sheet_titles)}\n")
print("All tabs:")
for i, title in enumerate(sheet_titles, 1):
    print(f"  {i}. {title}")

# Look for January tabs
jan_tabs = [t for t in sheet_titles if '1-' in t or 'jan' in t.lower() or 'january' in t.lower() or '1/28' in t or '1-28' in t]
if jan_tabs:
    print(f"\nJanuary-related tabs:")
    for tab in jan_tabs:
        print(f"  - {tab}")
else:
    print("\nNo January tabs found with common patterns")
