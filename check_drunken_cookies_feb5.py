#!/usr/bin/env python3
"""Check what was written to Drunken Cookies sheet for Feb 5"""
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

DRUNKEN_COOKIES_SHEET_ID = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"
TARGET_DATE = "2026-02-05"

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "service-account-key.json")

creds = service_account.Credentials.from_service_account_file(
    "service-account-key.json",
    scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
)
service = build("sheets", "v4", credentials=creds)

# Get all tabs
meta = service.spreadsheets().get(spreadsheetId=DRUNKEN_COOKIES_SHEET_ID).execute()
tab_titles = [s["properties"]["title"] for s in meta.get("sheets", [])]

print("=" * 60)
print("CHECKING DRUNKEN COOKIES SHEET FOR FEB 5")
print("=" * 60)
print(f"\nAvailable tabs: {tab_titles}")
print(f"\nLooking for date: {TARGET_DATE}")
print()

# Check each tab for Feb 5 data
for tab_name in ["Montehiedra", "San Patricio", "Plaza", "PlazaSol", "VSJ", "Plaza Carolina"]:
    if tab_name not in tab_titles:
        print(f"[X] {tab_name}: Tab not found!")
        continue
    
    print(f"\n[{tab_name}]")
    try:
        # Read column A to find the date row
        col_a = service.spreadsheets().values().get(
            spreadsheetId=DRUNKEN_COOKIES_SHEET_ID,
            range=f"'{tab_name}'!A:A"
        ).execute()
        col_a_values = col_a.get("values") or []
        
        # Find Feb 5 row
        date_row = None
        for i, row in enumerate(col_a_values):
            if row and str(row[0]).strip() == TARGET_DATE:
                date_row = i + 1
                break
        
        if date_row is None:
            print(f"  [X] No row found for {TARGET_DATE}")
            continue
        
        # Read the full row
        headers = service.spreadsheets().values().get(
            spreadsheetId=DRUNKEN_COOKIES_SHEET_ID,
            range=f"'{tab_name}'!1:1"
        ).execute()
        header_count = len((headers.get("values") or [[]])[0])
        
        row_data = service.spreadsheets().values().get(
            spreadsheetId=DRUNKEN_COOKIES_SHEET_ID,
            range=f"'{tab_name}'!A{date_row}:{chr(64+header_count)}{date_row}"
        ).execute()
        
        values = (row_data.get("values") or [[]])[0]
        print(f"  [OK] Row {date_row} found")
        print(f"  Values: {values[:5]}... (showing first 5)")
        
        # Count non-zero values
        non_zero = sum(1 for v in values[1:] if v and str(v).strip() not in ['0', '', '0.0'])
        print(f"  Non-zero cookie values: {non_zero}")
        
        if non_zero == 0:
            print(f"  [WARNING] All values are zero!")
        
    except Exception as e:
        print(f"  [ERROR] Error reading {tab_name}: {e}")

print("\n" + "=" * 60)
