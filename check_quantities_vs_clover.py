"""
Check if we're counting quantities correctly vs Clover site
"""

import sys
import codecs
from vm_inventory_updater_fixed import load_credentials
from datetime import datetime as dt, timedelta
from zoneinfo import ZoneInfo
import requests

# Fix Unicode encoding
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def check_quantities(creds, target_date):
    """Check quantities vs item counts"""
    merchant_id = creds.get('id')
    token = creds.get('token')
    
    tz = ZoneInfo('America/Puerto_Rico')
    start_time = dt(target_date.year, target_date.month, target_date.day, 0, 0, 0, 0, tz)
    end_time = dt(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tz)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    extended_start_ms = start_ms - (8 * 60 * 60 * 1000)
    extended_end_ms = end_ms + (4 * 60 * 60 * 1000)
    
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
    
    print(f"  Total orders: {len(orders)}")
    
    # Filter by date
    target_date_only = target_date.date()
    filtered_orders = []
    
    for order in orders:
        order_time_ms = order.get('createdTime', 0)
        if order_time_ms <= 0:
            continue
        
        order_dt_utc = dt.fromtimestamp(order_time_ms / 1000, tz=ZoneInfo('UTC'))
        order_dt_pr = order_dt_utc.astimezone(tz)
        order_date_pr = order_dt_pr.date()
        
        if order_date_pr == target_date_only:
            filtered_orders.append(order)
    
    print(f"  Orders on Feb 15: {len(filtered_orders)}")
    
    # Check Feb 14 orders (late orders)
    feb14_orders = []
    for order in orders:
        order_time_ms = order.get('createdTime', 0)
        if order_time_ms <= 0:
            continue
        
        order_dt_utc = dt.fromtimestamp(order_time_ms / 1000, tz=ZoneInfo('UTC'))
        order_dt_pr = order_dt_utc.astimezone(tz)
        order_date_pr = order_dt_pr.date()
        order_hour = order_dt_pr.hour
        
        if order_date_pr == target_date_only - timedelta(days=1) and order_hour >= 20:
            feb14_orders.append(order)
    
    print(f"  Feb 14 orders after 8 PM: {len(feb14_orders)}")
    
    # Count Brookie quantities
    print(f"\n[2/4] Counting Brookie quantities...")
    
    valid_states = ['locked', 'paid', 'open', 'completed']
    test_keywords = ['d:water', 'water', 'test', 'pick mini shots', 'shot glass', 'alcohol', 'don q', 'coco', 's:', 'x:', 'a:', ';;', '***', '...', 'empty']
    
    feb15_total_qty = 0
    feb15_item_count = 0
    feb14_late_total_qty = 0
    feb14_late_item_count = 0
    
    # Feb 15 orders
    for order in filtered_orders:
        order_state = order.get('state', '')
        if order_state not in valid_states:
            continue
        
        line_items_data = order.get('lineItems', {})
        line_items = line_items_data.get('elements', []) if isinstance(line_items_data, dict) else []
        
        for item in line_items:
            if isinstance(item, dict):
                item_name = item.get('name', '')
                item_name_lower = item_name.lower()
                quantity = item.get('unitQty', 0) or item.get('quantity', 0) or 1
                
                if 'brookie' in item_name_lower and 'F' in item_name:
                    # Check filters
                    if any(keyword in item_name_lower for keyword in test_keywords):
                        continue
                    
                    is_brookie = 'brookie' in item_name_lower and 'F' in item_name
                    is_cookie = is_brookie or 'cookie' in item_name_lower or 'chocolate' in item_name_lower
                    
                    if is_cookie:
                        feb15_total_qty += quantity
                        feb15_item_count += 1
    
    # Feb 14 late orders
    for order in feb14_orders:
        order_state = order.get('state', '')
        if order_state not in valid_states:
            continue
        
        line_items_data = order.get('lineItems', {})
        line_items = line_items_data.get('elements', []) if isinstance(line_items_data, dict) else []
        
        for item in line_items:
            if isinstance(item, dict):
                item_name = item.get('name', '')
                item_name_lower = item_name.lower()
                quantity = item.get('unitQty', 0) or item.get('quantity', 0) or 1
                
                if 'brookie' in item_name_lower and 'F' in item_name:
                    if any(keyword in item_name_lower for keyword in test_keywords):
                        continue
                    
                    is_brookie = 'brookie' in item_name_lower and 'F' in item_name
                    is_cookie = is_brookie or 'cookie' in item_name_lower or 'chocolate' in item_name_lower
                    
                    if is_cookie:
                        feb14_late_total_qty += quantity
                        feb14_late_item_count += 1
    
    print(f"\n[3/4] Results:")
    print(f"  Feb 15: {feb15_total_qty} total quantity ({feb15_item_count} items)")
    print(f"  Feb 14 late (8 PM+): {feb14_late_total_qty} total quantity ({feb14_late_item_count} items)")
    print(f"  Combined: {feb15_total_qty + feb14_late_total_qty} total quantity")
    
    print(f"\n[4/4] Comparison:")
    print(f"  Our API (Feb 15 only): {feb15_total_qty}")
    print(f"  Clover site: 123")
    print(f"  Difference: {123 - feb15_total_qty}")
    print(f"  If including Feb 14 late: {feb15_total_qty + feb14_late_total_qty}")
    print(f"  Difference with Feb 14: {123 - (feb15_total_qty + feb14_late_total_qty)}")

def main():
    print("=" * 80)
    print("CHECKING QUANTITIES VS CLOVER")
    print("=" * 80)
    
    creds_result = load_credentials()
    if isinstance(creds_result, tuple):
        clover_creds, _ = creds_result
    else:
        clover_creds = creds_result
    
    vsj_creds = clover_creds.get('VSJ')
    if not vsj_creds:
        print("[ERROR] VSJ credentials not found")
        return
    
    tz = ZoneInfo('America/Puerto_Rico')
    target_date = dt(2026, 2, 15, 0, 0, 0, 0, tz)
    
    check_quantities(vsj_creds, target_date)

if __name__ == "__main__":
    import datetime
    main()
