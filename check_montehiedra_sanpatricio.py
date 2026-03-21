#!/usr/bin/env python3
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

for tab in ["Montehiedra", "San Patricio"]:
    print(f"\n{'='*60}")
    print(f"{tab} - Feb 5, 2026")
    print('='*60)
    
    # Get headers
    headers = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{tab}'!1:1"
    ).execute().get("values", [[]])[0]
    
    # Find Feb 5 row
    col_a = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{tab}'!A:A"
    ).execute().get("values", [])
    
    date_row = None
    for i, row in enumerate(col_a):
        if row and str(row[0]).strip() == "2026-02-05":
            date_row = i + 1
            break
    
    if not date_row:
        print(f"  [X] No row found for 2026-02-05")
        continue
    
    # Get full row
    row_data = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"'{tab}'!A{date_row}:{chr(64+len(headers))}{date_row}"
    ).execute().get("values", [[]])[0]
    
    print(f"  Row: {date_row}")
    print(f"  Date: {row_data[0]}")
    print(f"\n  Cookie values:")
    for i, header in enumerate(headers[1:], 1):
        val = row_data[i] if i < len(row_data) else "0"
        if str(val).strip() not in ["0", "", "0.0"]:
            print(f"    {header}: {val}")
