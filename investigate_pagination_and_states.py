"""
Comprehensive investigation of pagination, lineItems expansion, and order state filtering
Focusing on the 3 problematic items: Brookie, Cornbread, Cherry Cake
"""

import sys
import codecs
from vm_inventory_updater_fixed import load_credentials
from datetime import datetime as dt, timedelta
from zoneinfo import ZoneInfo
import requests
import json

# Fix Unicode encoding
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def investigate_pagination_and_states(creds, target_date):
    """Comprehensive investigation"""
    merchant_id = creds.get('id')
    token = creds.get('token')
    store_name = creds.get('name', 'Unknown')
    
    tz = ZoneInfo('America/Puerto_Rico')
    start_time = dt(target_date.year, target_date.month, target_date.day, 0, 0, 0, 0, tz)
    end_time = dt(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tz)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    extended_start_ms = start_ms - (8 * 60 * 60 * 1000)
    extended_end_ms = end_ms + (4 * 60 * 60 * 1000)
    
    orders_url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
    
    print(f"\n[1/6] Testing pagination and lineItems expansion...")
    
    # Track problematic items
    problematic_items = {
        'Brookie': {'keyword': 'brookie', 'prefix': 'F'},
        'Cornbread': {'keyword': 'cornbread', 'prefix': 'G'},
        'Cherry Cake': {'keyword': 'cherry', 'prefix': None}
    }
    
    all_orders = []
    orders_without_lineitems = []
    orders_with_partial_lineitems = []
    
    # Fetch with pagination
    params = {
        'access_token': token,
        'filter': f'createdTime>={extended_start_ms}',
        'expand': 'lineItems',
        'limit': 1000
    }
    
    page_num = 0
    total_fetched = 0
    
    while True:
        page_num += 1
        print(f"  Fetching page {page_num}...")
        
        response = requests.get(orders_url, params=params, timeout=60)
        if response.status_code != 200:
            print(f"  [ERROR] API error on page {page_num}: {response.status_code}")
            break
        
        orders_data = response.json()
        page_orders = orders_data.get('elements', [])
        
        if not page_orders:
            break
        
        total_fetched += len(page_orders)
        print(f"    Page {page_num}: {len(page_orders)} orders")
        
        # Check lineItems expansion
        for order in page_orders:
            order_id = order.get('id', 'Unknown')
            line_items_data = order.get('lineItems', {})
            
            # Check if lineItems is expanded
            if not line_items_data:
                orders_without_lineitems.append(order_id)
            elif isinstance(line_items_data, dict):
                line_items = line_items_data.get('elements', [])
                if not line_items:
                    orders_with_partial_lineitems.append(order_id)
            
            all_orders.append(order)
        
        # Check if there are more pages
        if not orders_data.get('hasMore', False):
            break
        
        # Set offset for next page
        params['offset'] = total_fetched
    
    print(f"  Total orders fetched: {len(all_orders)}")
    print(f"  Orders without lineItems: {len(orders_without_lineitems)}")
    print(f"  Orders with partial lineItems: {len(orders_with_partial_lineitems)}")
    
    if orders_without_lineitems:
        print(f"  [WARNING] Sample orders without lineItems: {orders_without_lineitems[:5]}")
    
    # Filter by date
    print(f"\n[2/6] Filtering orders by date (Feb 15)...")
    target_date_only = target_date.date()
    filtered_orders = []
    
    for order in all_orders:
        order_time_ms = order.get('createdTime', 0)
        if order_time_ms <= 0:
            continue
        
        order_dt_utc = dt.fromtimestamp(order_time_ms / 1000, tz=ZoneInfo('UTC'))
        order_dt_pr = order_dt_utc.astimezone(tz)
        order_date_pr = order_dt_pr.date()
        
        if order_date_pr == target_date_only:
            filtered_orders.append(order)
    
    print(f"  Orders on Feb 15: {len(filtered_orders)}")
    
    # Analyze order states
    print(f"\n[3/6] Analyzing order states...")
    
    state_counts = {}
    for order in filtered_orders:
        state = order.get('state', 'UNKNOWN')
        state_counts[state] = state_counts.get(state, 0) + 1
    
    print(f"  Order states on Feb 15:")
    for state, count in sorted(state_counts.items()):
        print(f"    {state}: {count} orders")
    
    # Our valid states
    valid_states = ['locked', 'paid', 'open', 'completed']
    invalid_states = [s for s in state_counts.keys() if s not in valid_states]
    
    print(f"\n  Our valid states: {valid_states}")
    print(f"  States we filter out: {invalid_states}")
    if invalid_states:
        print(f"  Orders with invalid states: {sum(state_counts[s] for s in invalid_states)}")
    
    # Track problematic items by state
    print(f"\n[4/6] Tracking problematic items by state...")
    
    items_by_state = {item: {} for item in problematic_items.keys()}
    items_by_state_all = {item: {} for item in problematic_items.keys()}
    
    valid_states_set = set(valid_states)
    test_keywords = ['d:water', 'water', 'test', 'pick mini shots', 'shot glass', 'alcohol', 'don q', 'coco', 's:', 'x:', 'a:', ';;', '***', '...', 'empty']
    
    for order in filtered_orders:
        order_state = order.get('state', '')
        order_id = order.get('id', 'Unknown')
        
        line_items_data = order.get('lineItems', {})
        line_items = line_items_data.get('elements', []) if isinstance(line_items_data, dict) else []
        
        if not line_items:
            continue
        
        for item in line_items:
            if not isinstance(item, dict):
                continue
            
            item_name = item.get('name', '')
            item_name_lower = item_name.lower()
            quantity = item.get('unitQty', 0) or item.get('quantity', 0) or 1
            
            # Check each problematic item
            for item_key, item_config in problematic_items.items():
                keyword = item_config['keyword']
                prefix = item_config['prefix']
                
                matches = False
                if keyword == 'cherry':
                    matches = 'cherry' in item_name_lower and ('cake' in item_name_lower or 'red velvet' in item_name_lower)
                elif prefix:
                    matches = keyword in item_name_lower and prefix in item_name
                else:
                    matches = keyword in item_name_lower
                
                if matches:
                    # Count all states
                    if order_state not in items_by_state_all[item_key]:
                        items_by_state_all[item_key][order_state] = {'count': 0, 'quantity': 0, 'orders': []}
                    items_by_state_all[item_key][order_state]['count'] += 1
                    items_by_state_all[item_key][order_state]['quantity'] += quantity
                    items_by_state_all[item_key][order_state]['orders'].append(order_id)
                    
                    # Check filters
                    # Test keywords filter
                    if any(kw in item_name_lower for kw in test_keywords):
                        continue
                    
                    # State filter
                    if order_state not in valid_states_set:
                        continue
                    
                    # Cookie check
                    is_brookie = 'brookie' in item_name_lower and 'F' in item_name
                    is_cookie = (
                        is_brookie or
                        'cookie' in item_name_lower or
                        'chocolate' in item_name_lower or
                        'cornbread' in item_name_lower or
                        'cherry' in item_name_lower or
                        'cake' in item_name_lower or
                        'brownie' in item_name_lower
                    )
                    
                    if not is_cookie:
                        continue
                    
                    # Count valid states
                    if order_state not in items_by_state[item_key]:
                        items_by_state[item_key][order_state] = {'count': 0, 'quantity': 0}
                    items_by_state[item_key][order_state]['count'] += 1
                    items_by_state[item_key][order_state]['quantity'] += quantity
    
    # Report findings
    print(f"\n[5/6] Results for problematic items:")
    
    for item_key in problematic_items.keys():
        print(f"\n  {item_key}:")
        print(f"    ALL STATES (what Clover might count):")
        total_all = 0
        for state in sorted(items_by_state_all[item_key].keys()):
            qty = items_by_state_all[item_key][state]['quantity']
            count = items_by_state_all[item_key][state]['count']
            total_all += qty
            print(f"      {state}: {qty} quantity ({count} items)")
        print(f"    Total (all states): {total_all}")
        
        print(f"    VALID STATES (what we count):")
        total_valid = 0
        for state in sorted(items_by_state[item_key].keys()):
            qty = items_by_state[item_key][state]['quantity']
            count = items_by_state[item_key][state]['count']
            total_valid += qty
            print(f"      {state}: {qty} quantity ({count} items)")
        print(f"    Total (valid states): {total_valid}")
        
        if total_all != total_valid:
            diff = total_all - total_valid
            print(f"    [DIFFERENCE]: {diff} units filtered by state/filters")
            
            # Show which states are being filtered
            filtered_states = set(items_by_state_all[item_key].keys()) - set(items_by_state[item_key].keys())
            if filtered_states:
                print(f"    Filtered states: {sorted(filtered_states)}")
                for state in filtered_states:
                    qty = items_by_state_all[item_key][state]['quantity']
                    count = items_by_state_all[item_key][state]['count']
                    print(f"      {state}: {qty} quantity ({count} items)")
                    if count <= 5:
                        print(f"        Orders: {items_by_state_all[item_key][state]['orders']}")
    
    # Check for lineItems expansion issues
    print(f"\n[6/6] Checking for lineItems expansion issues...")
    
    orders_missing_items = []
    for order in filtered_orders:
        order_id = order.get('id', 'Unknown')
        order_state = order.get('state', '')
        
        line_items_data = order.get('lineItems', {})
        if not line_items_data:
            orders_missing_items.append((order_id, order_state, 'no_lineitems'))
            continue
        
        line_items = line_items_data.get('elements', []) if isinstance(line_items_data, dict) else []
        if not line_items:
            orders_missing_items.append((order_id, order_state, 'empty_lineitems'))
            continue
        
        # Check if any problematic items might be missing
        has_problematic = False
        for item in line_items:
            if isinstance(item, dict):
                item_name = item.get('name', '').lower()
                for item_key, item_config in problematic_items.items():
                    keyword = item_config['keyword']
                    prefix = item_config['prefix']
                    if keyword == 'cherry':
                        if 'cherry' in item_name and ('cake' in item_name or 'red velvet' in item_name):
                            has_problematic = True
                            break
                    elif prefix:
                        if keyword in item_name and prefix in item.get('name', ''):
                            has_problematic = True
                            break
                    else:
                        if keyword in item_name:
                            has_problematic = True
                            break
                if has_problematic:
                    break
    
    if orders_missing_items:
        print(f"  [WARNING] Found {len(orders_missing_items)} orders with lineItems issues")
        print(f"  Sample: {orders_missing_items[:5]}")
    else:
        print(f"  ✅ All orders have lineItems properly expanded")
    
    print(f"\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total orders fetched: {len(all_orders)}")
    print(f"Orders on Feb 15: {len(filtered_orders)}")
    print(f"Orders without lineItems: {len(orders_without_lineitems)}")
    print(f"Orders with partial lineItems: {len(orders_with_partial_lineitems)}")
    print(f"\nOrder states we filter out: {invalid_states}")
    if invalid_states:
        print(f"Total orders with invalid states: {sum(state_counts[s] for s in invalid_states)}")

def main():
    print("=" * 80)
    print("PAGINATION AND ORDER STATE INVESTIGATION")
    print("Focusing on: Brookie, Cornbread, Cherry Cake")
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
    
    investigate_pagination_and_states(vsj_creds, target_date)

if __name__ == "__main__":
    main()
