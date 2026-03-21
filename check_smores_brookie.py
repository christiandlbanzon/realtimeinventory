"""
Check S'mores and Brookie discrepancies mentioned in the message
Message says: S'mores sold 7 but malls pars says 5
Brookie sold 6 but malls pars says 4
"""

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
DRUNKEN_COOKIES_SHEET_ID = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"

def get_service():
    creds = Credentials.from_service_account_file(
        "service-account-key.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds)

def get_current_tab():
    tz = ZoneInfo("America/Puerto_Rico")
    now = datetime.now(tz)
    return f"{now.month}-{now.day}"

def check_live_sales(service, sheet_id, tab_name, location="Montehiedra"):
    """Check Live Sales values for S'mores and Brookie"""
    print(f"\n[1/2] Checking Live Sales in main PAR sheet (tab: {tab_name}, location: {location})...")
    
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"'{tab_name}'!A:ZZ"
        ).execute()
        
        values = result.get("values", [])
        if len(values) < 3:
            print("[ERROR] Not enough rows")
            return {}
        
        location_row = values[0]
        headers = values[1]
        cookie_rows = values[2:]
        
        # Find Live Sales column for Montehiedra
        live_sales_col = None
        for i, header in enumerate(headers):
            if header and "Live Sales Data" in str(header) and "Do Not Touch" in str(header):
                loc = location_row[i] if i < len(location_row) else ""
                if location.lower() in str(loc).lower():
                    live_sales_col = i
                    print(f"  Found Live Sales column for {location} at column {i+1}")
                    break
        
        if live_sales_col is None:
            print(f"[ERROR] Could not find Live Sales column for {location}")
            return {}
        
        # Find Brookie and S'mores rows
        results = {}
        for cookie_name, search_terms in [("Brookie", ["brookie", "F - Brookie"]), ("S'mores", ["s'mores", "smores", "L - S'mores"])]:
            cookie_row_idx = None
            for i, row in enumerate(cookie_rows):
                if row and row[0]:
                    first_cell = str(row[0]).lower()
                    for term in search_terms:
                        if term.lower() in first_cell:
                            cookie_row_idx = i
                            break
                    if cookie_row_idx is not None:
                        break
            
            if cookie_row_idx is not None:
                cookie_row = cookie_rows[cookie_row_idx]
                value = cookie_row[live_sales_col] if live_sales_col < len(cookie_row) else "0"
                results[cookie_name] = value
                print(f"  {cookie_name}: {value} (row {cookie_row_idx + 3})")
            else:
                results[cookie_name] = "NOT FOUND"
                print(f"  {cookie_name}: NOT FOUND")
        
        return results
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return {}

def check_drunken_cookies(service, tab_name, location="Montehiedra"):
    """Check Drunken Cookies Sheet values"""
    print(f"\n[2/2] Checking Drunken Cookies Sheet (tab: {location})...")
    
    try:
        # Get current date
        tz = ZoneInfo("America/Puerto_Rico")
        today = datetime.now(tz)
        date_str = today.strftime("%Y-%m-%d")
        
        result = service.spreadsheets().values().get(
            spreadsheetId=DRUNKEN_COOKIES_SHEET_ID,
            range=f"'{location}'!A:ZZ"
        ).execute()
        
        values = result.get("values", [])
        if not values:
            print("[ERROR] No data found")
            return {}
        
        headers = values[0]
        
        # Find date row
        date_row_idx = None
        for i, row in enumerate(values):
            if row and row[0] == date_str:
                date_row_idx = i
                break
        
        if date_row_idx is None:
            print(f"[WARNING] Date {date_str} not found, using most recent date")
            for i in range(len(values) - 1, max(0, len(values) - 10), -1):
                if values[i] and values[i][0] and ("-" in str(values[i][0]) or "/" in str(values[i][0])):
                    date_row_idx = i
                    print(f"  Using date: {values[i][0]}")
                    break
        
        if date_row_idx is None:
            print("[ERROR] Could not find date row")
            return {}
        
        date_row = values[date_row_idx]
        
        # Find columns for Brookie and S'mores
        results = {}
        for cookie_name, search_terms in [("Brookie", ["brookie", "F - Brookie"]), ("S'mores", ["s'mores", "smores", "L - S'mores"])]:
            cookie_col_idx = None
            for j, header in enumerate(headers):
                if header:
                    header_lower = str(header).lower()
                    for term in search_terms:
                        if term.lower() in header_lower:
                            cookie_col_idx = j
                            break
                    if cookie_col_idx is not None:
                        break
            
            if cookie_col_idx is not None and cookie_col_idx < len(date_row):
                value = date_row[cookie_col_idx] if date_row[cookie_col_idx] else "0"
                results[cookie_name] = value
                print(f"  {cookie_name}: {value} (column {headers[cookie_col_idx]})")
            else:
                results[cookie_name] = "NOT FOUND"
                print(f"  {cookie_name}: NOT FOUND")
        
        return results
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return {}

def main():
    print("=" * 80)
    print("CHECKING S'MORES AND BROOKIE DISCREPANCIES")
    print("Message: S'mores sold 7 but malls pars says 5")
    print("Message: Brookie sold 6 but malls pars says 4")
    print("=" * 80)
    
    service = get_service()
    tab_name = get_current_tab()
    
    print(f"\nCurrent tab: {tab_name}")
    print(f"Checking Montehiedra location")
    
    # Check Live Sales (malls pars)
    live_sales = check_live_sales(service, MAIN_SHEET_ID_FEB, tab_name, "Montehiedra")
    
    # Check Drunken Cookies Sheet
    drunken_cookies = check_drunken_cookies(service, tab_name, "Montehiedra")
    
    # Compare
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    
    for cookie_name in ["Brookie", "S'mores"]:
        print(f"\n{cookie_name}:")
        ls_value = live_sales.get(cookie_name, "NOT FOUND")
        dc_value = drunken_cookies.get(cookie_name, "NOT FOUND")
        
        print(f"  Live Sales (Mall PARs): {ls_value}")
        print(f"  Drunken Cookies Sheet: {dc_value}")
        
        try:
            ls_num = float(str(ls_value).replace(",", "")) if ls_value != "NOT FOUND" and ls_value else 0
            dc_num = float(str(dc_value).replace(",", "")) if dc_value != "NOT FOUND" and dc_value else 0
            
            if ls_num == dc_num:
                print(f"  [MATCH] Values are the same")
            else:
                print(f"  [DISCREPANCY] Difference: {dc_num - ls_num}")
                print(f"  Expected: {ls_value}, Actual: {dc_value}")
        except ValueError:
            if str(ls_value) != str(dc_value):
                print(f"  [DISCREPANCY] Values differ")
    
    print("\n" + "=" * 80)
    print("NOTE: The message mentioned:")
    print("  - S'mores: sold 7, malls pars says 5")
    print("  - Brookie: sold 6, malls pars says 4")
    print("=" * 80)

if __name__ == "__main__":
    main()
