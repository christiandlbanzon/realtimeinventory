#!/usr/bin/env python3
"""
Write a single test row to the Drunken Cookies sheet (Plaza tab) to verify
we can write. Run from real-time-inventory/ with service-account-key.json.

Usage: python write_drunken_cookies_test.py
"""
import os
from datetime import datetime

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "service-account-key.json")

from google.oauth2 import service_account
from googleapiclient.discovery import build

DRUNKEN_COOKIES_SHEET_ID = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"
TAB = "Plaza"

def main():
    print("Loading credentials...")
    creds = service_account.Credentials.from_service_account_file(
        "service-account-key.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    service = build("sheets", "v4", credentials=creds)
    print(f"Using account: {creds.service_account_email}")

    # Read Plaza tab: row 1 = headers, column A = dates
    print(f"Reading '{TAB}' tab...")
    meta = service.spreadsheets().get(spreadsheetId=DRUNKEN_COOKIES_SHEET_ID).execute()
    tab_titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
    if TAB not in tab_titles:
        print(f"ERROR: Tab '{TAB}' not found. Tabs: {tab_titles}")
        return 1

    headers_result = service.spreadsheets().values().get(
        spreadsheetId=DRUNKEN_COOKIES_SHEET_ID,
        range=f"'{TAB}'!1:1",
    ).execute()
    headers = (headers_result.get("values") or [[]])[0]
    if not headers or headers[0] != "Date":
        print(f"ERROR: Expected 'Date' in A1, got: {headers[:3]}")
        return 1

    col_a = service.spreadsheets().values().get(
        spreadsheetId=DRUNKEN_COOKIES_SHEET_ID,
        range=f"'{TAB}'!A:A",
    ).execute()
    col_a_values = col_a.get("values") or []
    # Append after last row
    date_str = datetime.now().strftime("%Y-%m-%d")
    test_row = [f"TEST {date_str}"]
    # One value per header (Date + cookie columns)
    test_row.extend([0] * (len(headers) - 1))
    date_row = len(col_a_values) + 1
    range_str = f"'{TAB}'!A{date_row}"

    print(f"Writing test row to {range_str}: {test_row[0]} ...")
    try:
        service.spreadsheets().values().update(
            spreadsheetId=DRUNKEN_COOKIES_SHEET_ID,
            range=range_str,
            valueInputOption="USER_ENTERED",
            body={"values": [test_row]},
        ).execute()
        print("OK: Write succeeded. Check the Drunken Cookies sheet (Plaza tab).")
        return 0
    except Exception as e:
        print(f"ERROR: {e}")
        if "permission" in str(e).lower() or "403" in str(e):
            print(f"Share the sheet with this account as Editor: {creds.service_account_email}")
        return 1

if __name__ == "__main__":
    exit(main())
