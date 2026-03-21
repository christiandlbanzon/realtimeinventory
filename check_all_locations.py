"""Diagnostic script to check ALL location columns and verify what's being written"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def column_to_letter(idx):
    """Convert column index to letter"""
    result = ""
    while idx >= 0:
        result = chr(65 + (idx % 26)) + result
        idx = idx // 26 - 1
    return result

def check_all_locations():
    """Check ALL Live Sales Data columns for all locations"""
    try:
        print("="*80)
        print("DIAGNOSTIC: Checking ALL Live Sales Data Columns")
        print("="*80)
        
        # Connect to Google Sheets
        creds = Credentials.from_service_account_file(
            "service-account-key.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        service = build("sheets", "v4", credentials=creds)
        
        sheet_id = "1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno"
        
        # Get current date tab
        tz = ZoneInfo("America/Puerto_Rico")
        now = datetime.now(tz)
        tab = f"{now.month}-{now.day}"
        
        print(f"\n[1/5] Reading sheet structure...")
        print(f"Sheet ID: {sheet_id}")
        print(f"Tab: {tab} (current date)")
        
        # Get all tabs
        sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        available_tabs = [sheet["properties"]["title"] for sheet in sheet_metadata.get("sheets", [])]
        print(f"Available tabs: {available_tabs[:10]}...")
        
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
        
        print(f"\n[2/5] Finding ALL 'Live Sales Data' columns...")
        
        # Find all Live Sales Data columns
        live_sales_columns = {}
        
        for i in range(len(headers)):
            header = str(headers[i]).lower() if i < len(headers) else ""
            location_name = str(location_row[i]) if i < len(location_row) else ""
            
            if "live sales data" in header and "do not touch" in header:
                column_letter = column_to_letter(i)
                live_sales_columns[column_letter] = {
                    "index": i,
                    "location": location_name,
                    "header": headers[i] if i < len(headers) else ""
                }
                print(f"\n  ✅ Column {column_letter} ({i}):")
                print(f"     Location: '{location_name}'")
                print(f"     Header: '{headers[i] if i < len(headers) else 'N/A'}'")
        
        if not live_sales_columns:
            print("\n  ❌ ERROR: No 'Live Sales Data (Do Not Touch)' columns found!")
            print("\n  Searching for any 'Live Sales' columns...")
            for i in range(len(headers)):
                header = str(headers[i]).lower() if i < len(headers) else ""
                if "live sales" in header:
                    print(f"    Column {column_to_letter(i)}: '{headers[i] if i < len(headers) else 'N/A'}'")
            return
        
        print(f"\n[3/5] Reading cookie names...")
        cookie_names = []
        for i, row in enumerate(cookie_rows):
            cookie_name = row[0] if row and row[0] else ""
            cookie_names.append(cookie_name)
            if i < 5:
                print(f"  Row {i+3}: '{cookie_name}'")
        
        print(f"\n[4/5] Checking values in each Live Sales Data column...")
        print("\n" + "="*80)
        print("SUMMARY: Current values in Live Sales Data columns")
        print("="*80)
        
        for col_letter, col_info in live_sales_columns.items():
            col_idx = col_info["index"]
            location = col_info["location"]
            
            # Read the column
            range_name = f"{tab}!{col_letter}3:{col_letter}20"
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            
            column_values = result.get("values", [])
            
            # Count non-zero values
            non_zero_count = 0
            total_sum = 0
            
            print(f"\n📍 {location} (Column {col_letter}):")
            print("-" * 80)
            
            for i in range(min(len(cookie_names), len(column_values))):
                cookie_name = cookie_names[i]
                value_str = column_values[i][0] if i < len(column_values) and column_values[i] else "0"
                
                try:
                    value = int(value_str) if value_str else 0
                    total_sum += value
                    if value > 0:
                        non_zero_count += 1
                        print(f"  Row {i+3:2d}: {cookie_name[:35]:35s} = {value}")
                except:
                    if value_str and value_str.strip():
                        non_zero_count += 1
                        print(f"  Row {i+3:2d}: {cookie_name[:35]:35s} = '{value_str}'")
            
            print(f"\n  Total cookies sold: {total_sum}")
            print(f"  Non-zero values: {non_zero_count}/{len(cookie_names)}")
            
            if total_sum == 0 and non_zero_count == 0:
                print(f"  ⚠️  WARNING: All values are zero/empty!")
        
        print("\n" + "="*80)
        print("[5/5] Checking what the main script would detect...")
        print("="*80)
        
        # Simulate the main script's detection logic
        location_mapping = {
            "Plaza": "Plaza Las Americas",
            "PlazaSol": "Plaza del Sol",
            "San Patricio": "San Patricio",
            "VSJ": "Old San Juan",
            "Montehiedra": "Montehiedra",
            "Plaza Carolina": "Plaza Carolina"
        }
        
        detected_columns = {}
        
        for i, header in enumerate(headers):
            if "Live Sales Data" in str(header) and "Do Not Touch" in str(header):
                if i < len(location_row) and location_row[i]:
                    location_name = str(location_row[i]).strip()
                    for mapped_location in location_mapping.values():
                        if mapped_location in location_name or location_name in mapped_location:
                            detected_columns[mapped_location] = i
                            print(f"✅ Detected {mapped_location} at column {column_to_letter(i)}")
                            break
        
        print(f"\nLocations detected by script: {len(detected_columns)}/{len(location_mapping)}")
        missing = set(location_mapping.values()) - set(detected_columns.keys())
        if missing:
            print(f"⚠️  Missing locations: {missing}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_all_locations()


