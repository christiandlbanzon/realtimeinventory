"""
Check discrepancies in Mall PARs (Monthly sheets)
Compare Live Sales values with what should be in the monthly PAR sheets
"""

import os
import sys
import codecs
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
from zoneinfo import ZoneInfo

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Sheet IDs
MAIN_SHEET_ID_FEB = "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4"
MAIN_SHEET_ID_JAN = "1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE"

# Items to check
ITEMS_TO_CHECK = {
    "Brookie": ["brookie", "F - Brookie", "*F* Brookie"],
    "Cornbread": ["cornbread", "Cornbread with Dulce de Leche", "G - Cornbread", "*G* Cornbread"],
    "Cherry Cake": ["cherry", "Cherry Cake", "Cherry", "Chocolate Cherry Cake", "Cherry Red Velvet Cake"]
}

def get_service():
    """Get Google Sheets service"""
    creds = Credentials.from_service_account_file(
        "service-account-key.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds)

def get_current_tab():
    """Get current date tab name"""
    tz = ZoneInfo("America/Puerto_Rico")
    now = datetime.now(tz)
    return f"{now.month}-{now.day}"

def get_main_sheet_id():
    """Get the main sheet ID based on current month"""
    tz = ZoneInfo("America/Puerto_Rico")
    now = datetime.now(tz)
    if now.month >= 2:  # February or later
        return MAIN_SHEET_ID_FEB, "February"
    else:
        return MAIN_SHEET_ID_JAN, "January"

def get_live_sales_values(service, tab_name, sheet_id):
    """Get values from Live Sales columns in main sheet"""
    print(f"\n[1/2] Reading Live Sales from {tab_name} tab...")
    
    try:
        # Read the sheet
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"'{tab_name}'!A:ZZ"
        ).execute()
        
        values = result.get("values", [])
        if not values or len(values) < 3:
            print(f"[WARNING] Not enough rows in sheet")
            return {}
        
        print(f"Found {len(values)} rows")
        
        # Row 0: Location names
        # Row 1: Headers (including "Live Sales Data (Do Not Touch)")
        # Row 2+: Cookie rows
        
        location_row = values[0] if len(values) > 0 else []
        headers = values[1] if len(values) > 1 else []
        cookie_rows = values[2:] if len(values) > 2 else []
        
        # Find all "Live Sales Data (Do Not Touch)" columns
        live_sales_columns = {}
        for i, header in enumerate(headers):
            if header and "Live Sales Data" in str(header) and "Do Not Touch" in str(header):
                # Get location name from location_row
                location = location_row[i] if i < len(location_row) else f"Column {i+1}"
                live_sales_columns[i] = location
                print(f"  Found Live Sales column {i+1}: {location}")
        
        if not live_sales_columns:
            print("[WARNING] No 'Live Sales Data (Do Not Touch)' columns found")
            return {}
        
        # Find cookie rows for each item
        results = {}
        for item_name, keywords in ITEMS_TO_CHECK.items():
            item_values = {}
            
            # Find the row for this cookie
            cookie_row_idx = None
            for i, row in enumerate(cookie_rows):
                if row and len(row) > 0:
                    first_cell = str(row[0]).lower()
                    for keyword in keywords:
                        if keyword.lower() in first_cell:
                            cookie_row_idx = i
                            break
                    if cookie_row_idx is not None:
                        break
            
            if cookie_row_idx is None:
                print(f"  {item_name}: Cookie row NOT FOUND")
                results[item_name] = "NOT FOUND"
                continue
            
            cookie_row = cookie_rows[cookie_row_idx]
            print(f"  {item_name}: Found at row {cookie_row_idx + 3}")
            
            # Get values from all Live Sales columns
            for col_idx, location in live_sales_columns.items():
                if col_idx < len(cookie_row):
                    value = cookie_row[col_idx] if cookie_row[col_idx] else "0"
                    item_values[location] = value
                    print(f"    {location}: {value}")
            
            results[item_name] = item_values
        
        return results
        
    except Exception as e:
        print(f"[ERROR] Error reading Live Sales: {e}")
        import traceback
        traceback.print_exc()
        return {}

def check_par_structure(service, sheet_id, tab_name):
    """Check the structure of the PAR sheet and verify Live Sales columns are correct"""
    print(f"\n[2/2] Checking PAR sheet structure...")
    
    try:
        # Read the sheet
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"'{tab_name}'!A:ZZ"
        ).execute()
        
        values = result.get("values", [])
        if not values or len(values) < 3:
            print(f"[WARNING] Not enough rows in sheet")
            return
        
        location_row = values[0] if len(values) > 0 else []
        headers = values[1] if len(values) > 1 else []
        
        print(f"\nPAR Sheet Structure:")
        print(f"  Location row: {[loc for loc in location_row[:15] if loc]}")
        print(f"  Headers: {[h for h in headers[:15] if h]}")
        
        # Check for Live Sales columns
        live_sales_cols = []
        for i, header in enumerate(headers):
            if header and "Live Sales Data" in str(header) and "Do Not Touch" in str(header):
                location = location_row[i] if i < len(location_row) else f"Column {i+1}"
                live_sales_cols.append((i, location, header))
        
        print(f"\n  Found {len(live_sales_cols)} 'Live Sales Data (Do Not Touch)' columns:")
        for col_idx, location, header in live_sales_cols:
            print(f"    Column {col_idx + 1} ({chr(65 + col_idx)}): {location} - {header}")
        
        # Check cookie rows
        cookie_rows = values[2:20] if len(values) > 2 else []
        print(f"\n  Cookie rows (first 5):")
        for i, row in enumerate(cookie_rows[:5]):
            if row and row[0]:
                print(f"    Row {i + 3}: {row[0]}")
        
        return live_sales_cols
        
    except Exception as e:
        print(f"[ERROR] Error checking PAR structure: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    print("=" * 80)
    print("CHECKING MALL PARS: Live Sales Data Verification")
    print("Items: Brookie, Cornbread, Cherry Cake")
    print("=" * 80)
    
    service = get_service()
    tab_name = get_current_tab()
    main_sheet_id, month_name = get_main_sheet_id()
    
    print(f"\nCurrent tab: {tab_name}")
    print(f"Month: {month_name}")
    print(f"Sheet ID: {main_sheet_id}")
    
    # Get Live Sales values
    live_sales_values = get_live_sales_values(service, tab_name, main_sheet_id)
    
    # Check PAR structure
    par_structure = check_par_structure(service, main_sheet_id, tab_name)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if live_sales_values:
        print(f"\nLive Sales values found for {len(live_sales_values)} items:")
        for item_name, item_values in live_sales_values.items():
            if isinstance(item_values, dict):
                print(f"\n  {item_name}:")
                for location, value in item_values.items():
                    print(f"    {location}: {value}")
            else:
                print(f"  {item_name}: {item_values}")
    
    if par_structure:
        print(f"\nPAR sheet has {len(par_structure)} Live Sales columns configured correctly.")
    else:
        print("\n[WARNING] Could not verify PAR structure.")

if __name__ == "__main__":
    main()
