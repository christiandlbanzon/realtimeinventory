"""Test script to verify VSJ (Old San Juan) Clover API access"""
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

def test_vsj_api():
    """Test VSJ Clover API access"""
    # Load credentials
    with open("clover_creds.json", "r") as f:
        creds_list = json.load(f)
    
    # Find VSJ credentials
    vsj_creds = None
    for cred in creds_list:
        if cred["name"] == "VSJ":
            vsj_creds = cred
            break
    
    if not vsj_creds:
        print("ERROR: VSJ credentials not found")
        return False
    
    print(f"Found VSJ credentials:")
    print(f"  Merchant ID: {vsj_creds['id']}")
    print(f"  Token: {vsj_creds['token'][:20]}...")
    print(f"  Category ID: {vsj_creds['cookie_category_id']}")
    
    # Test connectivity
    merchant_id = vsj_creds['id']
    token = vsj_creds['token']
    
    print(f"\n[1/4] Testing API connectivity...")
    try:
        response = requests.get(
            f"https://api.clover.com/v3/merchants/{merchant_id}/items",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            print(f"SUCCESS: API connectivity OK")
        else:
            print(f"ERROR: API returned status {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"ERROR: Cannot connect to API: {e}")
        return False
    
    # Get November 4th date range (the date showing in the sheet)
    print(f"\n[2/4] Getting November 4th date range...")
    tz = ZoneInfo("America/Puerto_Rico")
    target_date = datetime(2025, 11, 4, 0, 0, 0, 0, tz)
    start_time = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, 0, tz)
    end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tz)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    print(f"  Date: {target_date.strftime('%Y-%m-%d')}")
    print(f"  Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')} ({start_ms})")
    print(f"  End: {end_time.strftime('%Y-%m-%d %H:%M:%S')} ({end_ms})")
    
    # Fetch orders for November 4th
    print(f"\n[3/4] Fetching orders for November 4th...")
    try:
        url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
        params = {
            "filter": f"createdTime>={start_ms}",
            "expand": "lineItems,lineItems.item,lineItems.item.categories"
        }
        
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"ERROR: API returned status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
        
        orders = response.json().get("elements", [])
        print(f"SUCCESS: Found {len(orders)} orders")
        
        # Filter orders by date
        filtered_orders = []
        for order in orders:
            created_time = order.get("createdTime", 0)
            if start_ms <= created_time <= end_ms:
                filtered_orders.append(order)
        
        print(f"  Orders on Nov 4: {len(filtered_orders)}")
        
        # Count cookie sales
        print(f"\n[4/4] Counting cookie sales...")
        cookie_category_id = vsj_creds['cookie_category_id']
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
        
        print(f"\nCookie Sales Summary:")
        if cookie_sales:
            total = sum(cookie_sales.values())
            print(f"  Total cookies sold: {total}")
            for cookie, count in sorted(cookie_sales.items()):
                print(f"    {cookie}: {count}")
        else:
            print(f"  No cookie sales found on November 4th")
        
        if len(filtered_orders) > 0 and len(cookie_sales) == 0:
            print(f"\nWARNING: Found {len(filtered_orders)} orders but no cookie sales!")
            print(f"  This might indicate:")
            print(f"  1. Cookie category ID is incorrect")
            print(f"  2. Items are not categorized correctly in Clover")
            print(f"  3. Orders don't contain cookie items")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to fetch orders: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_vsj_api()

