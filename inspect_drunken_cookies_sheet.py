#!/usr/bin/env python3
"""Inspect Drunken Cookies sheet structure to understand its layout."""
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

DRUNKEN_COOKIES_SHEET_ID = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def main():
    creds = service_account.Credentials.from_service_account_file(
        "service-account-key.json", scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=creds)
    
    # Get sheet metadata
    meta = service.spreadsheets().get(spreadsheetId=DRUNKEN_COOKIES_SHEET_ID).execute()
    print("=== TABS ===")
    for s in meta.get("sheets", []):
        title = s["properties"]["title"]
        sheet_id = s["properties"]["sheetId"]
        rows = s["properties"].get("gridProperties", {}).get("rowCount", "?")
        cols = s["properties"].get("gridProperties", {}).get("columnCount", "?")
        print(f"  '{title}' (sheetId={sheet_id}, rows={rows}, cols={cols})")
    
    # Read first sheet - first 10 rows and headers
    sheets = meta.get("sheets", [])
    if not sheets:
        print("No sheets found")
        return
    
    first_tab = sheets[0]["properties"]["title"]
    print(f"\n=== FIRST 15 ROWS of '{first_tab}' (A:K) ===")
    result = service.spreadsheets().values().get(
        spreadsheetId=DRUNKEN_COOKIES_SHEET_ID,
        range=f"'{first_tab}'!A1:K15"
    ).execute()
    values = result.get("values", [])
    for i, row in enumerate(values, 1):
        print(f"  Row {i}: {row}")
    
    # Check around row 128 (where dates appear in screenshot)
    print(f"\n=== ROWS 125-135 of '{first_tab}' (A:H) ===")
    result2 = service.spreadsheets().values().get(
        spreadsheetId=DRUNKEN_COOKIES_SHEET_ID,
        range=f"'{first_tab}'!A125:H135"
    ).execute()
    values2 = result2.get("values", [])
    for i, row in enumerate(values2, 125):
        print(f"  Row {i}: {row[:8]}...")

if __name__ == "__main__":
    main()
