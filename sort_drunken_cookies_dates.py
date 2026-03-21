#!/usr/bin/env python3
"""Sort all rows in Drunken Cookies sheet tabs by date (chronological order)"""
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "service-account-key.json")

creds = service_account.Credentials.from_service_account_file(
    "service-account-key.json",
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
service = build("sheets", "v4", credentials=creds)
sheet_id = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"

# Get all tabs
meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
tab_titles = [s["properties"]["title"] for s in meta.get("sheets", [])]

print("=" * 70)
print("SORTING ROWS BY DATE IN DRUNKEN COOKIES SHEET")
print("=" * 70)

for tab_name in tab_titles:
    print(f"\n[{tab_name}]")
    try:
        # Get all data
        all_data = service.spreadsheets().values().get(
            spreadsheetId=sheet_id, range=f"'{tab_name}'!A:Z"
        ).execute().get("values", [])
        
        if len(all_data) < 2:
            print(f"  Skipping - not enough data")
            continue
        
        headers = all_data[0]
        data_rows = all_data[1:]
        
        # Parse dates and sort
        rows_with_dates = []
        for i, row in enumerate(data_rows):
            if not row or not row[0]:
                continue
            try:
                date_str = str(row[0]).strip()
                if date_str == "Date":
                    continue
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                rows_with_dates.append((date_obj, row, i + 2))  # +2 for header and 1-indexed
            except ValueError:
                continue
        
        if not rows_with_dates:
            print(f"  No date rows found")
            continue
        
        # Sort by date
        rows_with_dates.sort(key=lambda x: x[0])
        
        # Check if already sorted
        is_sorted = all(
            rows_with_dates[i][0] <= rows_with_dates[i+1][0]
            for i in range(len(rows_with_dates) - 1)
        )
        
        # Show current order for debugging
        if not is_sorted:
            print(f"  Current order (first 10 dates):")
            for date_obj, row, orig_row in rows_with_dates[:10]:
                print(f"    Row {orig_row}: {date_obj.strftime('%Y-%m-%d')}")
        
        print(f"  Sorting {len(rows_with_dates)} date rows...")
        
        # Get sheet ID for batch update
        sheet_id_num = None
        for sheet in meta.get("sheets", []):
            if sheet["properties"]["title"] == tab_name:
                sheet_id_num = sheet["properties"]["sheetId"]
                break
        
        if sheet_id_num is None:
            print(f"  ERROR: Could not find sheet ID")
            continue
        
        # Clear data rows (keep header)
        if len(data_rows) > 0:
            service.spreadsheets().values().clear(
                spreadsheetId=sheet_id,
                range=f"'{tab_name}'!A2:Z{len(all_data)}"
            ).execute()
        
        # Write sorted rows
        sorted_values = [headers] + [row for _, row, _ in rows_with_dates]
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"'{tab_name}'!A1",
            valueInputOption="USER_ENTERED",
            body={"values": sorted_values}
        ).execute()
        
        print(f"  [OK] Sorted {len(rows_with_dates)} rows chronologically")
        
    except Exception as e:
        print(f"  [ERROR] {e}")

print("\n" + "=" * 70)
print("Done!")
