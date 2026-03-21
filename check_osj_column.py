"""Diagnostic script to check Old San Juan column data"""
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def column_to_letter(idx):
    """Convert column index to letter"""
    result = ""
    while idx >= 0:
        result = chr(65 + (idx % 26)) + result
        idx = idx // 26 - 1
    return result

def check_old_san_juan_data():
    """Check what's actually in the Old San Juan column"""
    try:
        print("="*60)
        print("DIAGNOSTIC: Checking Old San Juan Column")
        print("="*60)
        
        # Connect to Google Sheets
        creds = Credentials.from_service_account_file(
            "service-account-key.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        service = build("sheets", "v4", credentials=creds)
        
        sheet_id = "1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno"
        tab = "11-4"
        
        print(f"\n[1/5] Reading sheet structure...")
        print(f"Sheet ID: {sheet_id}")
        print(f"Tab: {tab}")
        
        # Read full sheet
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{tab}!A:CC"
        ).execute()
        
        values = result.get("values", [])
        print(f"Total rows: {len(values)}")
        
        if len(values) < 3:
            print(f"ERROR: Not enough rows")
            return
        
        location_row = values[0]
        headers = values[1]
        cookie_rows = values[2:20]
        
        print(f"\n[2/5] Cookie names in column A:")
        cookie_names = []
        for i, row in enumerate(cookie_rows):
            cookie_name = row[0] if row and row[0] else ""
            cookie_names.append(cookie_name)
            print(f"  Row {i+3}: '{cookie_name}'")
        
        print(f"\n[3/5] Finding Old San Juan column...")
        osj_column = None
        
        # Check all columns
        for i in range(min(len(headers), len(location_row))):
            header = str(headers[i]).lower() if i < len(headers) else ""
            location_name = str(location_row[i]) if i < len(location_row) else ""
            
            if "old san juan" in location_name.lower():
                print(f"\n  Column {column_to_letter(i)} ({i}):")
                print(f"    Location: '{location_name}'")
                print(f"    Header: '{headers[i] if i < len(headers) else 'N/A'}'")
                
                if "live sales data" in header and "do not touch" in header:
                    osj_column = i
                    print(f"    ✅ MATCHED - This is the sales column!")
                elif "expected live inventory" in header:
                    print(f"    ⚠️  This is the INVENTORY column (wrong one)")
        
        if osj_column is None:
            print("\nERROR: Could not find Old San Juan sales column!")
            print("\nSearching more broadly...")
            for i in range(len(headers)):
                header = str(headers[i]).lower() if i < len(headers) else ""
                if "live sales data" in header and "do not touch" in header:
                    print(f"  Found 'Live Sales Data' at column {column_to_letter(i)}")
                    if i < len(location_row):
                        print(f"    Location: '{location_row[i]}'")
            return
        
        print(f"\n[4/5] Reading values from column {column_to_letter(osj_column)}...")
        
        # Read the Old San Juan column
        column_letter = column_to_letter(osj_column)
        range_name = f"{tab}!{column_letter}3:{column_letter}20"
        
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        
        column_values = result.get("values", [])
        
        print(f"\n[5/5] Current values in column {column_letter} (Old San Juan):")
        print(f"\nRow | Cookie Name | Current Value")
        print("-" * 60)
        
        total_non_zero = 0
        for i in range(len(cookie_names)):
            row_num = i + 3
            cookie_name = cookie_names[i]
            value = column_values[i][0] if i < len(column_values) and column_values[i] else "0"
            
            if value != "0" and value != "":
                total_non_zero += 1
            
            print(f"{row_num:3d} | {cookie_name[:30]:30s} | {value}")
        
        print("-" * 60)
        print(f"\nSummary:")
        print(f"  Total cookies: {len(cookie_names)}")
        print(f"  Non-zero values: {total_non_zero}")
        print(f"  Zero/empty values: {len(cookie_names) - total_non_zero}")
        
        if total_non_zero == 0:
            print("\n⚠️  WARNING: All values are zero or empty!")
            print("   The backfill script may not have written correctly.")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_old_san_juan_data()


