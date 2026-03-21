"""
Compare our logic vs Clover site logic
Check if Clover uses modifiedTime, different date ranges, or other logic
"""

import sys
import codecs
import datetime
from vm_inventory_updater_fixed import load_credentials
from datetime import datetime as dt
from zoneinfo import ZoneInfo
import requests

# Fix Unicode encoding
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def analyze_order_times(creds, target_date):
    """Analyze orders using both createdTime and modifiedTime"""
    merchant_id = creds.get('id')
    token = creds.get('token')
    
    tz = ZoneInfo('America/Puerto_Rico')
    start_time = dt(target_date.year, target_date.month, target_date.day, 0, 0, 0, 0, tz)
    end_time = dt(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tz)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    # Query wide range
    extended_start_ms = start_ms - (48 * 60 * 60 * 1000)  # 48 hours before
    extended_end_ms = end_ms + (24 * 60 * 60 * 1000)  # 24 hours after
    
    orders_url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
    params = {
        'access_token': token,
        'filter': f'createdTime>={extended_start_ms}',
        'expand': 'lineItems',
        'limit': 1000
    }
    
    print(f"\n[1/4] Fetching orders...")
    response = requests.get(orders_url, params=params, timeout=60)
    if response.status_code != 200:
        print(f"[ERROR] API error: {response.status_code}")
        return
    
    orders_data = response.json()
    orders = orders_data.get('elements', [])
    
    # Pagination
    offset = len(orders)
    while orders_data.get('hasMore', False) and offset < 10000:
        params['offset'] = offset
        paginated_response = requests.get(orders_url, params=params, timeout=60)
        if paginated_response.status_code == 200:
            paginated_data = paginated_response.json()
            paginated_orders = paginated_data.get('elements', [])
            orders.extend(paginated_orders)
            offset += len(paginated_orders)
            orders_data = paginated_data
        else:
            break
    
    print(f"  Total orders fetched: {len(orders)}")
    
    # Analyze Brookie items
    print(f"\n[2/4] Analyzing Brookie items by timestamp type...")
    
    target_date_only = target_date.date()
    
    by_created_feb15 = []
    by_modified_feb15 = []
    by_created_feb14 = []
    by_modified_feb14 = []
    
    for order in orders:
        order_state = order.get('state', '')
        order_id = order.get('id', 'Unknown')
        created_time_ms = order.get('createdTime', 0)
        modified_time_ms = order.get('modifiedTime', 0)
        
        if created_time_ms <= 0:
            continue
        
        # Convert createdTime
        created_dt_utc = dt.fromtimestamp(created_time_ms / 1000, tz=ZoneInfo('UTC'))
        created_dt_pr = created_dt_utc.astimezone(tz)
        created_date_pr = created_dt_pr.date()
        
        # Convert modifiedTime if available
        modified_date_pr = None
        if modified_time_ms > 0:
            modified_dt_utc = dt.fromtimestamp(modified_time_ms / 1000, tz=ZoneInfo('UTC'))
            modified_dt_pr = modified_dt_utc.astimezone(tz)
            modified_date_pr = modified_dt_pr.date()
        
        # Check for Brookie items
        line_items_data = order.get('lineItems', {})
        line_items = line_items_data.get('elements', []) if isinstance(line_items_data, dict) else []
        
        for item in line_items:
            if isinstance(item, dict):
                item_name = item.get('name', '')
                item_name_lower = item_name.lower()
                
                if 'brookie' in item_name_lower and 'F' in item_name:
                    item_info = {
                        'order_id': order_id,
                        'item_name': item_name,
                        'state': order_state,
                        'created_date': str(created_date_pr),
                        'created_time': created_dt_pr.strftime('%Y-%m-%d %H:%M:%S'),
                        'modified_date': str(modified_date_pr) if modified_date_pr else 'N/A',
                        'modified_time': modified_dt_pr.strftime('%Y-%m-%d %H:%M:%S') if modified_time_ms > 0 else 'N/A',
                    }
                    
                    # Categorize by createdTime
                    if created_date_pr == target_date_only:
                        by_created_feb15.append(item_info)
                    elif created_date_pr == target_date_only - datetime.timedelta(days=1):
                        by_created_feb14.append(item_info)
                    
                    # Categorize by modifiedTime
                    if modified_date_pr:
                        if modified_date_pr == target_date_only:
                            by_modified_feb15.append(item_info)
                        elif modified_date_pr == target_date_only - datetime.timedelta(days=1):
                            by_modified_feb14.append(item_info)
    
    print(f"\n[3/4] Results by createdTime:")
    print(f"  Feb 15: {len(by_created_feb15)} items")
    print(f"  Feb 14: {len(by_created_feb14)} items")
    
    print(f"\n[4/4] Results by modifiedTime:")
    print(f"  Feb 15: {len(by_modified_feb15)} items")
    print(f"  Feb 14: {len(by_modified_feb14)} items")
    
    # Check if combining Feb 14 late orders + Feb 15 = 123
    print(f"\n[ANALYSIS]:")
    print(f"  CreatedTime Feb 15 only: {len(by_created_feb15)}")
    print(f"  CreatedTime Feb 14 + Feb 15: {len(by_created_feb14) + len(by_created_feb15)}")
    print(f"  ModifiedTime Feb 15 only: {len(by_modified_feb15)}")
    print(f"  ModifiedTime Feb 14 + Feb 15: {len(by_modified_feb14) + len(by_modified_feb15)}")
    print(f"  Clover site shows: 123")
    
    # Check Feb 14 late orders (after certain time)
    feb14_late = [
        item for item in by_created_feb14
        if item['created_time'] >= '2026-02-14 20:00:00'
    ]
    print(f"\n  Feb 14 orders after 8 PM: {len(feb14_late)}")
    print(f"  Feb 15 + Feb 14 late (8 PM+): {len(by_created_feb15) + len(feb14_late)}")
    
    feb14_late_850 = [
        item for item in by_created_feb14
        if item['created_time'] >= '2026-02-14 20:50:00'
    ]
    print(f"  Feb 14 orders after 8:50 PM: {len(feb14_late_850)}")
    print(f"  Feb 15 + Feb 14 late (8:50 PM+): {len(by_created_feb15) + len(feb14_late_850)}")

def main():
    print("=" * 80)
    print("CLOVER LOGIC COMPARISON")
    print("Checking if Clover uses modifiedTime or different date logic")
    print("=" * 80)
    
    # Load credentials
    creds_result = load_credentials()
    if isinstance(creds_result, tuple):
        clover_creds, _ = creds_result
    else:
        clover_creds = creds_result
    
    vsj_creds = clover_creds.get('VSJ')
    if not vsj_creds:
        print("[ERROR] VSJ credentials not found")
        return
    
    # Target date: Feb 15, 2026
    tz = ZoneInfo('America/Puerto_Rico')
    target_date = dt(2026, 2, 15, 0, 0, 0, 0, tz)
    
    analyze_order_times(vsj_creds, target_date)

if __name__ == "__main__":
    main()
