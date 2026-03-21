"""
Check if Clover API values match what's in the sheets
For S'mores and Brookie discrepancies
"""

import sys
import codecs
import json
from vm_inventory_updater_fixed import fetch_clover_sales
from datetime import datetime
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def load_credentials():
    with open("clover_creds.json", "r") as f:
        return json.load(f)

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
    print("CHECKING CLOVER API vs SHEETS")
    print("For Montehiedra - Feb 15, 2026")
    print("=" * 80)
    
    # Get Clover data
    print("\n[1/2] Fetching from Clover API...")
    creds_list = load_credentials()
    montehiedra_creds = [c for c in creds_list if c.get('name') == 'Montehiedra'][0]
    
    tz = ZoneInfo('America/Puerto_Rico')
    target_date = datetime(2026, 2, 15, 0, 0, 0, 0, tz)
    
    clover_sales = fetch_clover_sales(montehiedra_creds, target_date)
    
    brookie_clover = clover_sales.get('F - Brookie', 0)
    smores_clover = clover_sales.get("L - S'mores", clover_sales.get("S'mores", 0))
    
    print(f"  Brookie: {brookie_clover}")
    print(f"  S'mores: {smores_clover}")
    
    # Get sheet data
    print("\n[2/2] Reading from sheets...")
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
    
    # Find Montehiedra Live Sales column
    montehiedra_col = None
    for i, header in enumerate(headers):
        if header and "Live Sales Data" in str(header) and "Do Not Touch" in str(header):
            loc = location_row[i] if i < len(location_row) else ""
            if "montehiedra" in str(loc).lower():
                montehiedra_col = i
                break
    
    # Find Brookie and S'mores rows
    brookie_sheet = None
    smores_sheet = None
    
    for i, row in enumerate(cookie_rows):
        if row and row[0]:
            first_cell = str(row[0]).lower()
            if "brookie" in first_cell and "F" in first_cell:
                brookie_sheet = row[montehiedra_col] if montehiedra_col < len(row) else "0"
            if "s'mores" in first_cell or "smores" in first_cell:
                smores_sheet = row[montehiedra_col] if montehiedra_col < len(row) else "0"
    
    print(f"  Brookie: {brookie_sheet}")
    print(f"  S'mores: {smores_sheet}")
    
    # Compare
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    
    try:
        brookie_clover_num = float(brookie_clover) if brookie_clover else 0
        brookie_sheet_num = float(str(brookie_sheet).replace(",", "")) if brookie_sheet else 0
        
        smores_clover_num = float(smores_clover) if smores_clover else 0
        smores_sheet_num = float(str(smores_sheet).replace(",", "")) if smores_sheet else 0
        
        print(f"\nBrookie:")
        print(f"  Clover API: {brookie_clover_num}")
        print(f"  Sheet: {brookie_sheet_num}")
        if brookie_clover_num == brookie_sheet_num:
            print(f"  [MATCH]")
        else:
            print(f"  [DISCREPANCY] Difference: {brookie_clover_num - brookie_sheet_num}")
        
        print(f"\nS'mores:")
        print(f"  Clover API: {smores_clover_num}")
        print(f"  Sheet: {smores_sheet_num}")
        if smores_clover_num == smores_sheet_num:
            print(f"  [MATCH]")
        else:
            print(f"  [DISCREPANCY] Difference: {smores_clover_num - smores_sheet_num}")
        
        print("\n" + "=" * 80)
        print("MESSAGE REFERENCE:")
        print("  - S'mores: sold 7, malls pars says 5")
        print("  - Brookie: sold 6, malls pars says 4")
        print("=" * 80)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
