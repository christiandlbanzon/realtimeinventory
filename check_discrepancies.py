"""
Check discrepancies between Drunken Cookies Sheet and Live Sales
for Brookie, Cornbread, and Cherry Cake
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
DRUNKEN_COOKIES_SHEET_ID = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"
# Main sheet (February)
MAIN_SHEET_ID_FEB = "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4"
# Main sheet (January)
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
        return MAIN_SHEET_ID_FEB
    else:
        return MAIN_SHEET_ID_JAN

def find_item_in_row(row_values, item_keywords):
    """Find item value in a row by checking if any keyword matches"""
    for cell_value in row_values:
        if cell_value:
            cell_lower = str(cell_value).lower()
            for keyword in item_keywords:
                if keyword.lower() in cell_lower:
                    return cell_value
    return None

def get_drunken_cookies_values(service):
    """Get values from Drunken Cookies Sheet for all stores"""
    print(f"\n[1/3] Reading Drunken Cookies Sheet...")
    
    try:
        # Get all tabs first
        sheet_metadata = service.spreadsheets().get(spreadsheetId=DRUNKEN_COOKIES_SHEET_ID).execute()
        available_tabs = [sheet["properties"]["title"] for sheet in sheet_metadata.get("sheets", [])]
        print(f"Available tabs: {available_tabs}")
        
        # Drunken Cookies sheet uses store names as tabs, not dates
        store_tabs = [t for t in available_tabs if t in ["San Patricio", "PlazaSol", "VSJ", "Montehiedra", "Plaza", "Plaza Carolina"]]
        
        if not store_tabs:
            print(f"[WARNING] No store tabs found in Drunken Cookies Sheet")
            return {}
        
        # Get current date - Drunken Cookies sheet uses YYYY-MM-DD format
        tz = ZoneInfo("America/Puerto_Rico")
        today = datetime.now(tz)
        date_str = today.strftime("%Y-%m-%d")  # e.g., "2026-02-15"
        
        all_results = {}  # {store: {item: value}}
        
        for store_tab in store_tabs:
            print(f"\n  Reading tab: {store_tab}")
            
            # Read the tab
            result = service.spreadsheets().values().get(
                spreadsheetId=DRUNKEN_COOKIES_SHEET_ID,
                range=f"'{store_tab}'!A:ZZ"
            ).execute()
            
            values = result.get("values", [])
            if not values:
                print(f"    No data found")
                continue
            
            # Find header row (usually row 1)
            headers = values[0] if values else []
            
            # Find date row (look for today's date in YYYY-MM-DD format)
            date_row_idx = None
            for i, row in enumerate(values):
                if row and len(row) > 0:
                    first_cell = str(row[0]).strip()
                    # Check for exact date match (YYYY-MM-DD format)
                    if date_str == first_cell or date_str in first_cell:
                        date_row_idx = i
                        break
            
            if date_row_idx is None:
                print(f"    Could not find date row for {date_str} (checking last few rows...)")
                # Try to find the most recent date row
                for i in range(len(values) - 1, max(0, len(values) - 10), -1):
                    row = values[i]
                    if row and len(row) > 0:
                        first_cell = str(row[0]).strip()
                        # Check if it looks like a date
                        if len(first_cell) >= 8 and ("-" in first_cell or "/" in first_cell):
                            date_row_idx = i
                            print(f"    Using most recent date row: {first_cell}")
                            break
                
                if date_row_idx is None:
                    print(f"    Skipping {store_tab} - no date found")
                    continue
            
            date_row = values[date_row_idx]
            store_results = {}
            
            # Extract values for each item
            for item_name, keywords in ITEMS_TO_CHECK.items():
                # For Cherry Cake, we need to handle multiple columns
                if item_name == "Cherry Cake":
                    # Find all cherry cake columns and sum them, or prioritize "Cherry Red Velvet Cake"
                    cherry_values = []
                    cherry_col_indices = []
                    
                    for j, header in enumerate(headers):
                        if header:
                            header_lower = str(header).lower()
                            # Prioritize "Cherry Red Velvet Cake" or "Cherry Cake"
                            if "cherry red velvet" in header_lower or ("cherry" in header_lower and "cake" in header_lower):
                                cherry_col_indices.append((j, header, "cherry red velvet" in header_lower))
                    
                    # Sort by priority (Cherry Red Velvet first)
                    cherry_col_indices.sort(key=lambda x: (not x[2], x[0]))
                    
                    if cherry_col_indices:
                        # Use the first (highest priority) column
                        item_col_idx, col_name, _ = cherry_col_indices[0]
                        if item_col_idx < len(date_row):
                            value = date_row[item_col_idx]
                            store_results[item_name] = value if value else "0"
                            print(f"      Using column: {col_name} = {value}")
                        else:
                            store_results[item_name] = "NOT FOUND"
                    else:
                        store_results[item_name] = "NOT FOUND"
                else:
                    # For other items, find first matching column
                    item_col_idx = None
                    for j, header in enumerate(headers):
                        if header:
                            header_lower = str(header).lower()
                            for keyword in keywords:
                                if keyword.lower() in header_lower:
                                    item_col_idx = j
                                    break
                            if item_col_idx is not None:
                                break
                    
                    if item_col_idx is not None and item_col_idx < len(date_row):
                        value = date_row[item_col_idx]
                        store_results[item_name] = value if value else "0"
                    else:
                        store_results[item_name] = "NOT FOUND"
            
            all_results[store_tab] = store_results
            print(f"    Found values for {len([v for v in store_results.values() if v != 'NOT FOUND'])} items")
        
        return all_results
        
    except Exception as e:
        print(f"[ERROR] Error reading Drunken Cookies Sheet: {e}")
        import traceback
        traceback.print_exc()
        return {}

def get_live_sales_values(service, tab_name, sheet_id):
    """Get values from Live Sales columns in main sheet"""
    print(f"\n[2/3] Reading Live Sales from main sheet (tab: {tab_name})...")
    
    try:
        # Read the sheet
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"'{tab_name}'!A:ZZ"
        ).execute()
        
        values = result.get("values", [])
        if not values or len(values) < 3:
            print(f"⚠️ Not enough rows in sheet")
            return {}
        
        print(f"Found {len(values)} rows")
        
        # Row 0: Location names
        # Row 1: Headers (including "Live Sales Data (Do Not Touch)")
        # Row 2+: Cookie rows
        
        location_row = values[0] if len(values) > 0 else []
        headers = values[1] if len(values) > 1 else []
        cookie_rows = values[2:] if len(values) > 2 else []
        
        print(f"Headers: {[h for h in headers[:15] if h]}")
        
        # Find all "Live Sales Data (Do Not Touch)" columns
        live_sales_columns = {}
        for i, header in enumerate(headers):
            if header and "Live Sales Data" in str(header) and "Do Not Touch" in str(header):
                # Get location name from location_row
                location = location_row[i] if i < len(location_row) else f"Column {i+1}"
                live_sales_columns[i] = location
                print(f"  Found Live Sales column {i+1}: {location}")
        
        if not live_sales_columns:
            print("⚠️ No 'Live Sales Data (Do Not Touch)' columns found")
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
        print(f"❌ Error reading Live Sales: {e}")
        import traceback
        traceback.print_exc()
        return {}

def compare_values(drunken_cookies_values, live_sales_values):
    """Compare values and report discrepancies"""
    print(f"\n[3/3] Comparing values...")
    print("=" * 80)
    
    discrepancies = []
    
    # Map store names between sheets
    store_mapping = {
        "Plaza": "Plaza Las Americas",
        "PlazaSol": "Plaza del Sol",
        "VSJ": "Old San Juan",
        "Montehiedra": "Montehiedra",
        "San Patricio": "San Patricio",
        "Plaza Carolina": "Plaza Carolina"
    }
    
    for item_name in ITEMS_TO_CHECK.keys():
        print(f"\n{item_name}:")
        print("-" * 80)
        
        # Compare each store
        for dc_store, dc_store_values in drunken_cookies_values.items():
            dc_value = dc_store_values.get(item_name, "NOT FOUND")
            
            # Find matching Live Sales location
            ls_location = store_mapping.get(dc_store, dc_store)
            ls_values = live_sales_values.get(item_name, {})
            ls_value = ls_values.get(ls_location, "NOT FOUND") if isinstance(ls_values, dict) else "NOT FOUND"
            
            print(f"  {dc_store}:")
            print(f"    Drunken Cookies: {dc_value}")
            print(f"    Live Sales ({ls_location}): {ls_value}")
            
            # Compare values
            try:
                dc_num = float(str(dc_value).replace(",", "")) if dc_value != "NOT FOUND" and dc_value else 0
                ls_num = float(str(ls_value).replace(",", "")) if ls_value != "NOT FOUND" and ls_value else 0
                
                if dc_num != ls_num:
                    discrepancies.append({
                        "item": item_name,
                        "store": dc_store,
                        "drunken_cookies": dc_value,
                        "live_sales": ls_value,
                        "difference": dc_num - ls_num
                    })
                    print(f"    [DISCREPANCY] Difference: {dc_num - ls_num}")
                else:
                    print(f"    [MATCH]")
            except ValueError:
                if str(dc_value) != str(ls_value):
                    discrepancies.append({
                        "item": item_name,
                        "store": dc_store,
                        "drunken_cookies": dc_value,
                        "live_sales": ls_value,
                        "difference": "N/A (non-numeric)"
                    })
                    print(f"    [DISCREPANCY] Values differ")
                else:
                    print(f"    [MATCH]")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if discrepancies:
        print(f"\n[WARNING] Found {len(discrepancies)} discrepancy(ies):\n")
        for disc in discrepancies:
            print(f"  {disc['item']} ({disc['store']}):")
            print(f"    Drunken Cookies: {disc['drunken_cookies']}")
            print(f"    Live Sales: {disc['live_sales']}")
            print(f"    Difference: {disc['difference']}")
            print()
    else:
        print("\n[OK] No discrepancies found! All values match.")
    
    return discrepancies

def main():
    print("=" * 80)
    print("CHECKING DISCREPANCIES: Drunken Cookies Sheet vs Live Sales")
    print("Items: Brookie, Cornbread, Cherry Cake")
    print("=" * 80)
    
    service = get_service()
    tab_name = get_current_tab()
    main_sheet_id = get_main_sheet_id()
    
    print(f"\nCurrent tab: {tab_name}")
    print(f"Main sheet ID: {main_sheet_id}")
    print(f"Drunken Cookies Sheet ID: {DRUNKEN_COOKIES_SHEET_ID}")
    
    # Get values from both sheets
    drunken_cookies_values = get_drunken_cookies_values(service)
    live_sales_values = get_live_sales_values(service, tab_name, main_sheet_id)
    
    # Compare
    discrepancies = compare_values(drunken_cookies_values, live_sales_values)
    
    return discrepancies

if __name__ == "__main__":
    main()
