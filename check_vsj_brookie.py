"""
Check VSJ Brookie discrepancy: Clover says 123, sheet shows 96
"""

import sys
import codecs
import json
from vm_inventory_updater_fixed import fetch_clover_sales, load_credentials
from datetime import datetime
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Fix Unicode encoding
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def get_sheet_service():
    creds = Credentials.from_service_account_file(
        "service-account-key.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds)

def main():
    print("=" * 80)
    print("CHECKING VSJ BROOKIE DISCREPANCY")
    print("Clover site: 123")
    print("Sheet: 96")
    print("Difference: 27 units missing")
    print("=" * 80)
    
    # Get Clover API data for VSJ
    print("\n[1/3] Fetching from Clover API (VSJ/Old San Juan)...")
    creds_result = load_credentials()
    # load_credentials returns (clover_creds, shopify_creds)
    if isinstance(creds_result, tuple):
        clover_creds, _ = creds_result
    else:
        clover_creds = creds_result
    
    vsj_creds = clover_creds.get('VSJ') if isinstance(clover_creds, dict) else None
    
    if not vsj_creds:
        print("[ERROR] VSJ credentials not found")
        print(f"Available locations: {list(clover_creds.keys()) if isinstance(clover_creds, dict) else 'N/A'}")
        return
    
    tz = ZoneInfo('America/Puerto_Rico')
    target_date = datetime(2026, 2, 15, 0, 0, 0, 0, tz)
    
    clover_sales = fetch_clover_sales(vsj_creds, target_date)
    
    # Check all Brookie-related items
    brookie_items = {k: v for k, v in clover_sales.items() if 'brookie' in k.lower() or ('F' in k and 'brookie' in k.lower())}
    
    print(f"\nClover API results for Feb 15, 2026:")
    print(f"  Total Brookie items found: {len(brookie_items)}")
    for item_name, count in brookie_items.items():
        print(f"    {item_name}: {count}")
    
    total_brookie_clover = sum(brookie_items.values())
    print(f"\n  TOTAL BROOKIE (sum of all): {total_brookie_clover}")
    
    # Get sheet data
    print("\n[2/3] Reading from sheet (Old San Juan Live Sales)...")
    service = get_sheet_service()
    sheet_id = "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4"
    tab_name = "2-15"
    
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"'{tab_name}'!A:ZZ"
    ).execute()
    
    values = result.get("values", [])
    location_row = values[0]
    headers = values[1]
    cookie_rows = values[2:]
    
    # Find Old San Juan Live Sales column
    vsj_col = None
    for i, header in enumerate(headers):
        if header and "Live Sales Data" in str(header) and "Do Not Touch" in str(header):
            loc = location_row[i] if i < len(location_row) else ""
            if "old san juan" in str(loc).lower() or "vsj" in str(loc).lower():
                vsj_col = i
                print(f"  Found Old San Juan Live Sales column at column {i+1}")
                break
    
    # Find Brookie row
    brookie_sheet = None
    brookie_row_idx = None
    for i, row in enumerate(cookie_rows):
        if row and row[0]:
            first_cell = str(row[0]).lower()
            if "brookie" in first_cell and "F" in first_cell:
                brookie_row_idx = i
                brookie_sheet = row[vsj_col] if vsj_col < len(row) else "0"
                print(f"  Found Brookie at row {i + 3}: {row[0]}")
                print(f"  Sheet value: {brookie_sheet}")
                break
    
    # Compare
    print("\n[3/3] COMPARISON")
    print("=" * 80)
    
    try:
        brookie_clover_num = float(total_brookie_clover)
        brookie_sheet_num = float(str(brookie_sheet).replace(",", "")) if brookie_sheet else 0
        
        print(f"\nBrookie for VSJ/Old San Juan (Feb 15, 2026):")
        print(f"  Clover API: {brookie_clover_num}")
        print(f"  Sheet: {brookie_sheet_num}")
        print(f"  Difference: {brookie_clover_num - brookie_sheet_num}")
        
        if brookie_clover_num == brookie_sheet_num:
            print(f"  [MATCH]")
        else:
            print(f"  [DISCREPANCY] Missing {brookie_clover_num - brookie_sheet_num} units in sheet")
            print(f"\n  This needs investigation!")
            print(f"  Possible causes:")
            print(f"    1. Orders filtered out by date range")
            print(f"    2. Orders filtered out by order state")
            print(f"    3. Multiple Brookie items not being consolidated")
            print(f"    4. Date filtering issue")
        
        print("\n" + "=" * 80)
        print("NEXT STEPS:")
        print("  1. Check if orders are being filtered incorrectly")
        print("  2. Verify date filtering logic")
        print("  3. Check order state filtering")
        print("  4. Verify consolidation logic")
        print("=" * 80)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
