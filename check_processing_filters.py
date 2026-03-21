"""
Check what filters are removing Brookie items during processing
"""

import sys
import codecs
from vm_inventory_updater_fixed import load_credentials
from datetime import datetime as dt
from zoneinfo import ZoneInfo
import requests

# Fix Unicode encoding
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def check_filters(creds, target_date):
    """Check what filters are removing items"""
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
    
    print(f"\n[1/3] Fetching orders...")
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
    
    # Filter by date (Feb 15 only)
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
    
    # Now check Brookie items and apply all filters
    print(f"\n[2/3] Checking Brookie items with filters...")
    
    all_brookie = []
    filtered_by_state = []
    filtered_by_test = []
    filtered_by_non_cookie = []
    passed_all_filters = []
    
    valid_states = ['locked', 'paid', 'open', 'completed']
    test_keywords = ['d:water', 'water', 'test', 'pick mini shots', 'shot glass', 'alcohol', 'don q', 'coco', 's:', 'x:', 'a:', ';;', '***', '...', 'empty']
    
    for order in filtered_orders:
        order_state = order.get('state', '')
        order_id = order.get('id', 'Unknown')
        
        line_items_data = order.get('lineItems', {})
        line_items = line_items_data.get('elements', []) if isinstance(line_items_data, dict) else []
        
        for item in line_items:
            if isinstance(item, dict):
                item_name = item.get('name', '')
                item_name_lower = item_name.lower()
                
                if 'brookie' in item_name_lower and 'F' in item_name:
                    all_brookie.append({
                        'order_id': order_id,
                        'item_name': item_name,
                        'state': order_state
                    })
                    
                    # Check state filter
                    if order_state not in valid_states:
                        filtered_by_state.append({
                            'order_id': order_id,
                            'item_name': item_name,
                            'state': order_state
                        })
                        continue
                    
                    # Check test keywords
                    if any(keyword in item_name_lower for keyword in test_keywords):
                        filtered_by_test.append({
                            'order_id': order_id,
                            'item_name': item_name,
                            'state': order_state
                        })
                        continue
                    
                    # Check if cookie (Brookie should pass)
                    is_brookie = 'brookie' in item_name_lower and 'F' in item_name
                    is_cookie = (
                        is_brookie or
                        'cookie' in item_name_lower or
                        'chocolate' in item_name_lower or
                        'brownie' in item_name_lower
                    )
                    
                    if not is_cookie:
                        filtered_by_non_cookie.append({
                            'order_id': order_id,
                            'item_name': item_name,
                            'state': order_state
                        })
                        continue
                    
                    # Passed all filters
                    passed_all_filters.append({
                        'order_id': order_id,
                        'item_name': item_name,
                        'state': order_state
                    })
    
    print(f"\n[3/3] Filter Results:")
    print(f"  Total Brookie items: {len(all_brookie)}")
    print(f"  Filtered by state: {len(filtered_by_state)}")
    print(f"  Filtered by test keywords: {len(filtered_by_test)}")
    print(f"  Filtered by non-cookie: {len(filtered_by_non_cookie)}")
    print(f"  Passed all filters: {len(passed_all_filters)}")
    
    print(f"\n  Clover site: 123")
    print(f"  Our count: {len(passed_all_filters)}")
    print(f"  Difference: {123 - len(passed_all_filters)}")
    
    if filtered_by_state:
        print(f"\n  Sample filtered by state:")
        for item in filtered_by_state[:5]:
            print(f"    Order {item['order_id']}: {item['item_name']} - State: {item['state']}")
    
    if filtered_by_test:
        print(f"\n  Sample filtered by test:")
        for item in filtered_by_test[:5]:
            print(f"    Order {item['order_id']}: {item['item_name']}")

def main():
    print("=" * 80)
    print("CHECKING PROCESSING FILTERS")
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
    
    check_filters(vsj_creds, target_date)

if __name__ == "__main__":
    main()
