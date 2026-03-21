"""Backfill Old San Juan sales data for November 4th"""
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from fuzzywuzzy import fuzz

def column_to_letter(idx):
    """Convert column index to letter (0=A, 1=B, etc.)"""
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
    
    # Remove special characters and prefixes
    cleaned = cleaned.replace("*", "").replace("-", "").strip()
    
    # Common mappings
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
    
    # Try exact match first
    cleaned_lower = cleaned.lower()
    for api_pattern, sheet_name in name_mapping.items():
        if api_pattern in cleaned_lower:
            return sheet_name
    
    return cleaned

def fetch_vsj_sales_for_date(target_date):
    """Fetch VSJ sales data for a specific date"""
    # Load VSJ credentials
    with open("clover_creds.json", "r") as f:
        creds_list = json.load(f)
    
    vsj_creds = None
    for cred in creds_list:
        if cred["name"] == "VSJ":
            vsj_creds = cred
            break
    
    if not vsj_creds:
        print("ERROR: VSJ credentials not found")
        return {}
    
    merchant_id = vsj_creds['id']
    token = vsj_creds['token']
    cookie_category_id = vsj_creds['cookie_category_id']
    
    # Convert date to timestamp range
    tz = ZoneInfo("America/Puerto_Rico")
    start_time = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, 0, tz)
    end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tz)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    print(f"Fetching VSJ orders for {target_date.strftime('%Y-%m-%d')}...")
    print(f"  Time range: {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Fetch orders
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
            print(f"Response: {response.text[:500]}")
            break
        
        data = response.json()
        orders = data.get("elements", [])
        
        if not orders:
            break
        
        all_orders.extend(orders)
        
        if len(orders) < limit:
            break
        
        offset += limit
    
    print(f"Found {len(all_orders)} total orders")
    
    # Filter orders by date
    filtered_orders = []
    for order in all_orders:
        created_time = order.get("createdTime", 0)
        if start_ms <= created_time <= end_ms:
            filtered_orders.append(order)
    
    print(f"Orders on {target_date.strftime('%Y-%m-%d')}: {len(filtered_orders)}")
    
    # Count cookie sales
    cookie_sales = {}
    
    for order in filtered_orders:
        line_items = order.get("lineItems", {}).get("elements", [])
        for item in line_items:
            item_data = item.get("item", {})
            categories = item_data.get("categories", {}).get("elements", [])
            
            # Check if item belongs to cookie category
            is_cookie = any(cat.get("id") == cookie_category_id for cat in categories)
            
            if is_cookie:
                item_name = item_data.get("name", "Unknown")
                # Each line item = 1 unit sold
                cookie_sales[item_name] = cookie_sales.get(item_name, 0) + 1
    
    # Clean and consolidate cookie names
    cleaned_sales = {}
    for api_name, count in cookie_sales.items():
        cleaned_name = clean_cookie_name(api_name)
        if cleaned_name:
            cleaned_sales[cleaned_name] = cleaned_sales.get(cleaned_name, 0) + count
    
    return cleaned_sales

def find_cookie_row(cookie_names, target_cookie):
    """Find row number for a cookie in the sheet"""
    # Try exact match first
    for i, cookie in enumerate(cookie_names):
        if cookie == target_cookie:
            return i + 3  # Row 3 is first cookie row (1-indexed)
    
    # Try fuzzy match
    best_match = None
    best_score = 0
    
    for cookie in cookie_names:
        score = fuzz.ratio(target_cookie.lower(), cookie.lower())
        if score > best_score:
            best_score = score
            best_match = cookie
    
    if best_score >= 80:  # 80% similarity threshold
        for i, cookie in enumerate(cookie_names):
            if cookie == best_match:
                return i + 3
    
    return None

def backfill_old_san_juan():
    """Backfill Old San Juan sales data for November 4th"""
    try:
        print("="*60)
        print("OLD SAN JUAN SALES DATA BACKFILL")
        print("="*60)
        
        # Step 1: Fetch sales data
        target_date = datetime(2025, 11, 4, 0, 0, 0, 0, ZoneInfo("America/Puerto_Rico"))
        sales_data = fetch_vsj_sales_for_date(target_date)
        
        if not sales_data:
            print("ERROR: No sales data found")
            return False
        
        total_sales = sum(sales_data.values())
        print(f"\nTotal cookies sold: {total_sales}")
        print("Cookie breakdown:")
        for cookie, count in sorted(sales_data.items()):
            print(f"  {cookie}: {count}")
        
        # Step 2: Connect to Google Sheets
        print("\n[2/4] Connecting to Google Sheets...")
        creds = Credentials.from_service_account_file(
            "service-account-key.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        service = build("sheets", "v4", credentials=creds)
        
        sheet_id = "1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno"
        tab = "11-4"
        
        print(f"Sheet: {sheet_id}")
        print(f"Tab: {tab}")
        
        # Step 3: Read sheet structure
        print("\n[3/4] Reading sheet structure...")
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{tab}!A:CC"
        ).execute()
        
        values = result.get("values", [])
        if len(values) < 3:
            print(f"ERROR: Not enough rows in sheet (found {len(values)})")
            return False
        
        location_row = values[0]
        headers = values[1]
        cookie_names = [row[0] for row in values[2:20] if row and row[0]]
        
        print(f"Found {len(cookie_names)} cookie rows")
        
        # Step 4: Find Old San Juan column (BU)
        print("\n[4/4] Finding Old San Juan column...")
        osj_column = None
        
        for i in range(len(headers)):
            header = str(headers[i]).lower() if i < len(headers) else ""
            location_name = str(location_row[i]) if i < len(location_row) else ""
            
            if ("old san juan" in location_name.lower() and 
                "live sales data" in header and 
                "do not touch" in header):
                osj_column = i
                print(f"Found Old San Juan column at {column_to_letter(i)}")
                break
        
        if osj_column is None:
            print("ERROR: Could not find Old San Juan column!")
            return False
        
        # Step 5: Prepare updates
        print("\n[5/5] Preparing updates...")
        updates = []
        
        for cookie_name, sales_count in sales_data.items():
            row_num = find_cookie_row(cookie_names, cookie_name)
            
            if row_num:
                cell_range = f"{tab}!{column_to_letter(osj_column)}{row_num}"
                updates.append({
                    "range": cell_range,
                    "values": [[str(sales_count)]]
                })
                print(f"  {cookie_name}: {sales_count} -> {cell_range}")
            else:
                print(f"  WARNING: Could not find row for '{cookie_name}'")
        
        if not updates:
            print("ERROR: No updates to make")
            return False
        
        # Step 6: Write to sheet
        print(f"\nWriting {len(updates)} updates to sheet...")
        body = {
            "valueInputOption": "RAW",
            "data": updates
        }
        
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id,
            body=body
        ).execute()
        
        print("SUCCESS: Old San Juan sales data backfilled!")
        print(f"Updated {len(updates)} cookie rows")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    backfill_old_san_juan()



