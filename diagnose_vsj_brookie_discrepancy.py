"""
Comprehensive diagnosis of VSJ Brookie discrepancy
Clover site: 123
Our API: 97
Missing: 26 units
"""

import sys
import codecs
import json
from vm_inventory_updater_fixed import load_credentials
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

# Fix Unicode encoding
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def fetch_all_orders_detailed(creds, target_date):
    """Fetch all orders and analyze in detail"""
    merchant_id = creds.get('id')
    token = creds.get('token')
    
    tz = ZoneInfo('America/Puerto_Rico')
    start_time = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, 0, tz)
    end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tz)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    # Expand query range to catch all possible orders
    extended_start_ms = start_ms - (48 * 60 * 60 * 1000)  # 48 hours before
    extended_end_ms = end_ms + (24 * 60 * 60 * 1000)  # 24 hours after
    
    orders_url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
    params = {
        'access_token': token,
        'filter': f'createdTime>={extended_start_ms}',
        'expand': 'lineItems',
        'limit': 1000
    }
    
    print(f"\n[1/5] Fetching orders from API...")
    response = requests.get(orders_url, params=params, timeout=60)
    if response.status_code != 200:
        print(f"[ERROR] API error: {response.status_code}")
        return []
    
    orders_data = response.json()
    orders = orders_data.get('elements', [])
    
    # Handle pagination
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
            print(f"  Fetched {len(paginated_orders)} more orders (total: {len(orders)})")
        else:
            break
    
    print(f"  Total orders fetched: {len(orders)}")
    return orders

def analyze_brookie_detailed(orders, target_date):
    """Detailed analysis of Brookie items"""
    tz = ZoneInfo('America/Puerto_Rico')
    target_date_only = target_date.date()
    
    print(f"\n[2/5] Analyzing Brookie items...")
    
    all_brookie_items = []
    by_date = {}
    by_state = {}
    filtered_by_test = []
    filtered_by_non_cookie = []
    
    for order in orders:
        order_state = order.get('state', '')
        order_id = order.get('id', 'Unknown')
        order_time_ms = order.get('createdTime', 0)
        
        if order_time_ms <= 0:
            continue
        
        # Convert to Puerto Rico time
        order_dt_utc = datetime.fromtimestamp(order_time_ms / 1000, tz=ZoneInfo('UTC'))
        order_dt_pr = order_dt_utc.astimezone(tz)
        order_date_pr = order_dt_pr.date()
        
        # Check for Brookie items
        line_items_data = order.get('lineItems', {})
        line_items = line_items_data.get('elements', []) if isinstance(line_items_data, dict) else []
        
        for item in line_items:
            if isinstance(item, dict):
                item_name = item.get('name', '')
                item_name_lower = item_name.lower()
                
                # Check if this is a Brookie item
                if 'brookie' in item_name_lower and 'F' in item_name:
                    item_info = {
                        'order_id': order_id,
                        'item_name': item_name,
                        'state': order_state,
                        'date_pr': str(order_date_pr),
                        'time_pr': order_dt_pr.strftime('%Y-%m-%d %H:%M:%S %Z'),
                        'is_target_date': order_date_pr == target_date_only,
                        'will_process': order_state in ['locked', 'paid', 'open', 'completed'],
                        'is_test': any(kw in item_name_lower for kw in ['test', 'd:water', 'water', 'pick mini shots']),
                        'is_cookie': any(kw in item_name_lower for kw in ['cookie', 'brookie', 'chocolate', 'brownie'])
                    }
                    all_brookie_items.append(item_info)
                    
                    # Categorize
                    date_key = str(order_date_pr)
                    if date_key not in by_date:
                        by_date[date_key] = []
                    by_date[date_key].append(item_info)
                    
                    if order_state not in by_state:
                        by_state[order_state] = []
                    by_state[order_state].append(item_info)
                    
                    if item_info['is_test']:
                        filtered_by_test.append(item_info)
                    if not item_info['is_cookie']:
                        filtered_by_non_cookie.append(item_info)
    
    return all_brookie_items, by_date, by_state, filtered_by_test, filtered_by_non_cookie

def main():
    print("=" * 80)
    print("VSJ BROOKIE DISCREPANCY DIAGNOSIS")
    print("Clover site: 123")
    print("Our API: 97")
    print("Missing: 26 units")
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
    target_date = datetime(2026, 2, 15, 0, 0, 0, 0, tz)
    
    # Fetch all orders
    all_orders = fetch_all_orders_detailed(vsj_creds, target_date)
    
    # Analyze Brookie items
    all_brookie, by_date, by_state, filtered_test, filtered_non_cookie = analyze_brookie_detailed(all_orders, target_date)
    
    print(f"\n[3/5] Summary Statistics:")
    print(f"  Total Brookie items found: {len(all_brookie)}")
    print(f"  By date:")
    for date_key in sorted(by_date.keys()):
        count = len(by_date[date_key])
        print(f"    {date_key}: {count} items")
    
    print(f"\n  By state:")
    for state_key in sorted(by_state.keys()):
        count = len(by_state[state_key])
        will_process = sum(1 for item in by_state[state_key] if item['will_process'])
        print(f"    {state_key}: {count} items ({will_process} will process)")
    
    # Count items that would be included (Feb 15 + valid state)
    target_date_str = str(target_date.date())
    included_items = [
        item for item in all_brookie
        if item['is_target_date'] and item['will_process'] and not item['is_test'] and item['is_cookie']
    ]
    
    print(f"\n[4/5] Items that would be INCLUDED (Feb 15 + valid state + not test + is cookie):")
    print(f"  Count: {len(included_items)}")
    
    # Count items that would be EXCLUDED
    excluded_items = [
        item for item in all_brookie
        if item not in included_items
    ]
    
    print(f"\n[5/5] Items that would be EXCLUDED:")
    print(f"  Total excluded: {len(excluded_items)}")
    
    excluded_by_reason = {
        'not_feb15': [item for item in excluded_items if not item['is_target_date']],
        'invalid_state': [item for item in excluded_items if item['is_target_date'] and not item['will_process']],
        'test_item': [item for item in excluded_items if item['is_test']],
        'not_cookie': [item for item in excluded_items if not item['is_cookie']]
    }
    
    for reason, items in excluded_by_reason.items():
        if items:
            print(f"\n  {reason}: {len(items)} items")
            # Show sample items
            for item in items[:5]:
                print(f"    Order {item['order_id']}: {item['item_name']} - Date: {item['date_pr']}, State: {item['state']}")
    
    print("\n" + "=" * 80)
    print("ANALYSIS:")
    print(f"  Included count: {len(included_items)}")
    print(f"  Clover site count: 123")
    print(f"  Difference: {123 - len(included_items)}")
    print("=" * 80)
    
    # Check if Clover might be using a different date range
    print("\n[POSSIBLE ISSUES]:")
    print("  1. Clover site might include Feb 14 orders (business day logic)")
    print("  2. Clover site might use modifiedTime instead of createdTime")
    print("  3. Clover site might include orders with different states")
    print("  4. Clover site might not filter test items")
    print("  5. Pagination might be missing some orders")

if __name__ == "__main__":
    main()
