#!/usr/bin/env python3
"""Check actual date order in sheet"""
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "service-account-key.json")

creds = service_account.Credentials.from_service_account_file(
    "service-account-key.json",
    scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
)
service = build("sheets", "v4", credentials=creds)
sheet_id = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"

for tab_name in ["Montehiedra", "San Patricio"]:
    print(f"\n[{tab_name}]")
    
    # Get column A
    col_a = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{tab_name}'!A:A"
    ).execute().get("values", [])
    
    # Find dates around Feb 2-5
    print("  Dates around Feb 2-5:")
    for i, row in enumerate(col_a[125:140], start=126):  # Check rows 126-140
        if row and row[0]:
            date_str = str(row[0]).strip()
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                if date_obj.month == 2 and 2 <= date_obj.day <= 5:
                    print(f"    Row {i}: {date_str}")
            except ValueError:
                pass
