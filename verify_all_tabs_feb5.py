#!/usr/bin/env python3
"""Verify Feb 5 data exists in ALL tabs of Drunken Cookies sheet"""
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "service-account-key.json")

creds = service_account.Credentials.from_service_account_file(
    "service-account-key.json",
    scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
)
service = build("sheets", "v4", credentials=creds)
sheet_id = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"

# Get all tabs
meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
tab_titles = [s["properties"]["title"] for s in meta.get("sheets", [])]

print("=" * 70)
print("VERIFYING FEB 5 DATA IN DRUNKEN COOKIES SHEET")
print("=" * 70)
print(f"\nSheet ID: {sheet_id}")
print(f"Available tabs: {tab_titles}")
print(f"\nLooking for date: 2026-02-05")
print()

for tab_name in tab_titles:
    print(f"\n[{tab_name}]")
    
    # Find Feb 5 row
    col_a = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{tab_name}'!A:A"
    ).execute().get("values", [])
    
    date_row = None
    for i, row in enumerate(col_a):
        if row and str(row[0]).strip() == "2026-02-05":
            date_row = i + 1
            break
    
    if not date_row:
        print(f"  [X] NO ROW FOUND for 2026-02-05")
        print(f"      Last date in column A: {col_a[-1][0] if col_a and col_a[-1] else 'N/A'}")
        continue
    
    # Get headers
    headers = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{tab_name}'!1:1"
    ).execute().get("values", [[]])[0]
    
    # Get full row
    row_data = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"'{tab_name}'!A{date_row}:{chr(64+len(headers))}{date_row}"
    ).execute().get("values", [[]])[0]
    
    # Count non-zero values
    non_zero = []
    for i, header in enumerate(headers[1:], 1):
        val = row_data[i] if i < len(row_data) else "0"
        val_str = str(val).strip()
        if val_str not in ["0", "", "0.0"]:
            non_zero.append(f"{header}: {val}")
    
    print(f"  [OK] Row {date_row} found")
    print(f"  Date: {row_data[0]}")
    print(f"  Non-zero values: {len(non_zero)}")
    if non_zero:
        print(f"  Values: {', '.join(non_zero[:5])}{'...' if len(non_zero) > 5 else ''}")
    else:
        print(f"  [WARNING] All values are ZERO!")

print("\n" + "=" * 70)
