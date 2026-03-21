"""Comprehensive backfill script for ALL locations - fills Live Sales Data columns"""
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from fuzzywuzzy import fuzz

def column_to_letter(idx):
    """Convert column index to letter"""
    result = ""
    while idx >= 0:
        result = chr(65 + (idx % 26)) + result
        idx = idx // 26 - 1
    return result

def clean_cookie_name(api_name):
    """Clean cookie names from API to match sheet names"""
    if not api_name:
        return ""
    
    cleaned = api_name.strip()
    
    # Use the same mapping as vm_inventory_updater.py
    name_mapping = {
        "chocolate chip nutella": "A - Chocolate Chip Nutella",
        "signature chocolate chip": "B - Signature Chocolate Chip",
        "cookies & cream": "C - Cookies & Cream",
        "cookies and cream": "C - Cookies & Cream",
        "white chocolate macadamia": "D - White Chocolate Macadamia",
        "churro with dulce de leche": "E - Churro with Dulce De Leche",
        "churro with dulce de leche": "E - Churro with Dulce De Leche",
        "almond chocolate": "F - Almond Chocolate",
        "pecan creme brulee": "G - Pecan Creme Brulee",
        "pecan crème brûlée": "G - Pecan Creme Brulee",
        "cheesecake with biscoff": "H - Cheesecake with Biscoff",
        "guava crumble": "I - Guava Crumble",
        "creepy mummy matcha": "J - Creepy Mummy Matcha",
        "strawberry cheesecake": "K - Strawberry Cheesecake",
        "smores": "L - S'mores",
        "s'mores": "L - S'mores",
        "dubai chocolate": "M - Dubai Chocolate",
        "chocolate cheesecake": "N - Chocolate Cheesecake",
    }
    
    cleaned_lower = cleaned.lower()
    for api_pattern, sheet_name in name_mapping.items():
        if api_pattern in cleaned_lower:
            return sheet_name
    
    return cleaned

def fetch_clover_sales_for_location(creds, target_date):
    """Fetch Clover sales for a specific location and date"""
    merchant_id = creds['id']
    token = creds['token']
    cookie_category_id = creds['cookie_category_id']
    
    tz = ZoneInfo("America/Puerto_Rico")
    start_time = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, 0, tz)
    end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tz)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
    params = {
        "filter": f"createdTime>={start_ms}",
        "expand": "lineItems,lineItems.item,lineItems.item.categories"
    }
    
    all_orders = []
    offset = 0
    limit = 100
    
    while True:
        params_with_limit = {**params, "limit": limit, "offset": offset}
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params_with_limit,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"ERROR: API returned status {response.status_code}")
            break
        
        data = response.json()
        orders = data.get("elements", [])
        
        if not orders:
            break
        
        all_orders.extend(orders)
        
        if len(orders) < limit:
            break
        
        offset += limit
    
    # Filter orders by date
    filtered_orders = []
    for order in all_orders:
        created_time = order.get("createdTime", 0)
        if start_ms <= created_time <= end_ms:
            filtered_orders.append(order)
    
    # Count cookie sales
    cookie_sales = {}
    
    for order in filtered_orders:
        line_items = order.get("lineItems", {}).get("elements", [])
        for item in line_items:
            item_data = item.get("item", {})
            categories = item_data.get("categories", {}).get("elements", [])
            
            is_cookie = any(cat.get("id") == cookie_category_id for cat in categories)
            
            if is_cookie:
                item_name = item_data.get("name", "Unknown")
                cookie_sales[item_name] = cookie_sales.get(item_name, 0) + 1
    
    # Clean and consolidate
    cleaned_sales = {}
    for api_name, count in cookie_sales.items():
        cleaned_name = clean_cookie_name(api_name)
        if cleaned_name:
            cleaned_sales[cleaned_name] = cleaned_sales.get(cleaned_name, 0) + count
    
    return cleaned_sales

def find_cookie_row(cookie_names, target_cookie):
    """Find row number for a cookie"""
    for i, cookie in enumerate(cookie_names):
        if cookie == target_cookie:
            return i + 3
    
    # Fuzzy match
    best_match = None
    best_score = 0
    
    for cookie in cookie_names:
        score = fuzz.ratio(target_cookie.lower(), cookie.lower())
        if score > best_score:
            best_score = score
            best_match = cookie
    
    if best_score >= 80:
        for i, cookie in enumerate(cookie_names):
            if cookie == best_match:
                return i + 3
    
    return None

def backfill_all_locations():
    """Backfill Live Sales Data for ALL locations"""
    try:
        print("="*80)
        print("COMPREHENSIVE BACKFILL: All Locations Live Sales Data")
        print("="*80)
        
        # Load credentials
        with open("clover_creds.json", "r") as f:
            creds_list = json.load(f)
        
        # Map credentials to sheet locations
        cred_to_sheet = {
            "Plaza": "Plaza Las Americas",
            "PlazaSol": "Plaza del Sol",
            "San Patricio": "San Patricio",
            "VSJ": "Old San Juan",
            "Montehiedra": "Montehiedra",
            "Plaza Carolina": "Plaza Carolina"
        }
        
        # Step 1: Fetch sales data for all locations
        target_date = datetime(2025, 11, 5, 0, 0, 0, 0, ZoneInfo("America/Puerto_Rico"))
        print(f"\n[1/5] Fetching sales data for {target_date.strftime('%Y-%m-%d')}...")
        
        all_sales = {}
        for cred in creds_list:
            location_name = cred["name"]
            if location_name in cred_to_sheet:
                print(f"  Fetching {location_name}...")
                sales = fetch_clover_sales_for_location(cred, target_date)
                sheet_location = cred_to_sheet[location_name]
                all_sales[sheet_location] = sales
                total = sum(sales.values())
                print(f"    {sheet_location}: {total} cookies sold")
        
        # Step 2: Connect to Google Sheets
        print("\n[2/5] Connecting to Google Sheets...")
        creds = Credentials.from_service_account_file(
            "service-account-key.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        service = build("sheets", "v4", credentials=creds)
        
        sheet_id = "1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno"
        tab = "11-5"  # November 5th
        
        print(f"Sheet: {sheet_id}")
        print(f"Tab: {tab}")
        
        # Step 3: Read sheet structure
        print("\n[3/5] Reading sheet structure...")
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{tab}!A:CC"
        ).execute()
        
        values = result.get("values", [])
        if len(values) < 3:
            print(f"ERROR: Not enough rows")
            return False
        
        location_row = values[0]
        headers = values[1]
        cookie_names = [row[0] for row in values[2:20] if row and row[0]]
        
        print(f"Found {len(cookie_names)} cookie rows")
        
        # Step 4: Find ALL Live Sales Data columns
        print("\n[4/5] Finding Live Sales Data columns...")
        location_columns = {}
        
        for i, header in enumerate(headers):
            if "Live Sales Data" in str(header) and "Do Not Touch" in str(header):
                location_name = str(location_row[i]).strip() if i < len(location_row) and location_row[i] else ""
                
                # Match to known locations
                for sheet_location in cred_to_sheet.values():
                    location_lower = location_name.lower()
                    sheet_lower = sheet_location.lower()
                    if sheet_lower in location_lower or location_lower in sheet_lower:
                        if sheet_location not in location_columns:
                            location_columns[sheet_location] = i
                            print(f"  ✅ {sheet_location}: Column {column_to_letter(i)}")
                            break
        
        print(f"\nFound {len(location_columns)} locations")
        
        # Step 5: Prepare and write updates
        print("\n[5/5] Preparing updates...")
        updates = []
        
        for sheet_location, sales_data in all_sales.items():
            if sheet_location not in location_columns:
                print(f"  ⚠️  Skipping {sheet_location} - column not found")
                continue
            
            col_idx = location_columns[sheet_location]
            print(f"\n  📝 {sheet_location} (Column {column_to_letter(col_idx)}):")
            
            for cookie_name, sales_count in sales_data.items():
                row_num = find_cookie_row(cookie_names, cookie_name)
                
                if row_num:
                    cell_range = f"{tab}!{column_to_letter(col_idx)}{row_num}"
                    updates.append({
                        "range": cell_range,
                        "values": [[str(sales_count)]]
                    })
                    print(f"    {cookie_name}: {sales_count} -> {cell_range}")
        
        if not updates:
            print("ERROR: No updates to make")
            return False
        
        # Write to sheet
        print(f"\nWriting {len(updates)} updates to sheet...")
        body = {
            "valueInputOption": "RAW",
            "data": updates
        }
        
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id,
            body=body
        ).execute()
        
        print("\n" + "="*80)
        print("SUCCESS: All locations backfilled!")
        print(f"Updated {len(updates)} cookie rows across {len(location_columns)} locations")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    backfill_all_locations()


