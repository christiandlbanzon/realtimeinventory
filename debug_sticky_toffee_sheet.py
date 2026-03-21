#!/usr/bin/env python3
"""
Debug script: Why is Sticky Toffee Pudding data "far from" the label?
Checks sheet structure, cookie row, location columns, and where data is written.
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from datetime import timedelta

# Add project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "service-account-key.json")

from google.oauth2 import service_account
from googleapiclient.discovery import build

# Use March sheet (current)
SHEET_ID = "1kYbyeLoOd986lZrnc57XOynanYLbW2NM2fwypUJa2PQ"  # March Mall PARs_2026
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def column_to_letter(i):
    result = ""
    while i >= 0:
        result = chr(65 + (i % 26)) + result
        i = i // 26 - 1
    return result


def main():
    creds = service_account.Credentials.from_service_account_file(
        "service-account-key.json", scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=creds)

    # Get tab name (March format)
    meta = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    tabs = [s["properties"]["title"] for s in meta.get("sheets", [])]
    # Use yesterday's tab
    from datetime import date
    yesterday_date = date.today() - timedelta(days=1)
    yesterday_str = yesterday_date.strftime("%m-%d")  # "03-08"
    yesterday_alt = f"{int(yesterday_date.strftime('%m'))}-{int(yesterday_date.strftime('%d'))}"  # "3-8"
    sheet_tab = tabs[0] if tabs else "03-01"
    for t in tabs:
        if yesterday_str in t or yesterday_alt in t or t == yesterday_str or t == yesterday_alt:
            sheet_tab = t
            break
    # Fallback: last tab (most recent = yesterday)
    if not any(yesterday_str in t or yesterday_alt in t for t in tabs):
        sheet_tab = tabs[-1] if tabs else "03-01"
    print(f"Available tabs: {tabs[:15]}...")

    print(f"=== DEBUG: Sticky Toffee Pudding - Sheet structure ===")
    print(f"Sheet ID: {SHEET_ID}")
    print(f"Tab: {sheet_tab}")
    print()

    # Read full sheet
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=f"'{sheet_tab}'!A1:CC120",
    ).execute()
    values = result.get("values", [])

    if len(values) < 3:
        print("ERROR: Sheet has < 3 rows")
        return

    location_row = values[0]
    headers = values[1]
    print(f"First 12 cols - Row 0 (location): {[str(location_row[i])[:20] if i < len(location_row) else '' for i in range(12)]}")
    print(f"First 12 cols - Row 1 (headers):  {[str(headers[i])[:25] if i < len(headers) else '' for i in range(12)]}")
    print()

    # Find G - Sticky Toffee Pudding row
    sticky_row_idx = None
    cookie_names = []
    for i, row in enumerate(values[2:], start=3):
        if row and row[0]:
            name = str(row[0]).strip()
            cookie_names.append(name)
            if "sticky" in name.lower() and "toffee" in name.lower():
                sticky_row_idx = i
                print(f"Found 'Sticky Toffee' at sheet row {i}: '{name}'")
                break

    if sticky_row_idx is None:
        print("ERROR: Sticky Toffee Pudding row not found!")
        print("Cookie names in column A:", cookie_names[:20])
        return

    # Check cookie_names slice used by updater (rows 3-19 only!)
    cookie_names_updater = [row[0] for row in values[2:19] if row and row[0]]
    sticky_in_updater = any("sticky" in str(c).lower() and "toffee" in str(c).lower() for c in cookie_names_updater)
    print(f"\nUpdater only reads rows 3-19 ({len(cookie_names_updater)} cookies). Sticky Toffee in range: {sticky_in_updater}")

    if not sticky_in_updater and sticky_row_idx > 19:
        print("*** BUG: Sticky Toffee is at row {sticky_row_idx} but updater only reads rows 3-19! ***")

    # Get the Sticky Toffee row data
    row_data = values[sticky_row_idx - 1] if sticky_row_idx <= len(values) else []
    print(f"\n=== Row {sticky_row_idx} (Sticky Toffee) - non-empty cells ===")
    gaps = 0
    last_col_with_data = -1
    for j, cell in enumerate(row_data):
        val = str(cell).strip() if cell else ""
        if val:
            col_letter = column_to_letter(j)
            loc = location_row[j] if j < len(location_row) else ""
            hdr = headers[j] if j < len(headers) else ""
            gap = j - last_col_with_data - 1 if last_col_with_data >= 0 else j
            if gap > 0 and last_col_with_data >= 0:
                gaps += gap
            last_col_with_data = j
            print(f"  {col_letter}{sticky_row_idx}: '{val}'  | location: '{loc}' | header: '{hdr}'")
        elif j < 15:  # Show first 15 columns even if empty
            col_letter = column_to_letter(j)
            loc = location_row[j] if j < len(location_row) else ""
            hdr = headers[j] if j < len(headers) else ""
            print(f"  {col_letter}{sticky_row_idx}: (empty)  | location: '{loc}' | header: '{hdr}'")

    # Find "Live Sales Data (Do Not Touch)" columns
    print(f"\n=== Live Sales Data (Do Not Touch) columns ===")
    for j, hdr in enumerate(headers):
        if "Live Sales Data" in str(hdr) and "Do Not Touch" in str(hdr):
            loc = location_row[j] if j < len(location_row) else ""
            val = row_data[j] if j < len(row_data) else ""
            print(f"  Col {column_to_letter(j)} (idx {j}): location='{loc}', header='{hdr[:50]}...', value='{val}'")

    # Gap analysis
    first_data_col = next((j for j, c in enumerate(row_data) if c and str(c).strip()), None)
    if first_data_col is not None:
        print(f"\n=== Gap analysis ===")
        print(f"  Column A = cookie name. First data at column {column_to_letter(first_data_col)} (index {first_data_col})")
        print(f"  Gap: {first_data_col - 1} columns between A and first data")
        if first_data_col > 5:
            print(f"  *** Possible issue: Large gap ({first_data_col - 1} cols) - check if column mapping is correct")


if __name__ == "__main__":
    main()
