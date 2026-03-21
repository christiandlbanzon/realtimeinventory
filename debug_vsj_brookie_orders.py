"""
Debug VSJ Brookie orders - find why we're missing 27 units
Clover site: 123
Our API: 96
Sheet: 96
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

def fetch_all_orders(creds, start_date, end_date):
    """Fetch all orders in date range, including filtered ones"""
    merchant_id = creds.get('id')
    token = creds.get('token')
    
    tz = ZoneInfo('America/Puerto_Rico')
    start_time = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, 0, tz)
    end_time = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, 999999, tz)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    # Expand query range to catch all possible orders
    extended_start_ms = start_ms - (24 * 60 * 60 * 1000)  # 24 hours before
    extended_end_ms = end_ms + (24 * 60 * 60 * 1000)  # 24 hours after
    
    orders_url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
    params = {
        'access_token': token,
        'filter': f'createdTime>={extended_start_ms}',
        'expand': 'lineItems',
        'limit': 1000
    }
    
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
        else:
            break
    
    return orders

def analyze_brookie_orders(orders, target_date):
    """Analyze all Brookie orders"""
    tz = ZoneInfo('America/Puerto_Rico')
    target_date_only = target_date.date()
    
    all_brookie_orders = []
    filtered_out = []
    included = []
    
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
        
        brookie_count = 0
        for item in line_items:
            if isinstance(item, dict):
                item_name = item.get('name', '')
                if 'brookie' in item_name.lower() and 'F' in item_name:
                    brookie_count += 1
        
        if brookie_count > 0:
            order_info = {
                'order_id': order_id,
                'state': order_state,
                'date_pr': str(order_date_pr),
                'time_pr': order_dt_pr.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'brookie_count': brookie_count,
                'is_target_date': order_date_pr == target_date_only,
                'will_process': order_state in ['locked', 'paid', 'open', 'completed']
            }
            all_brookie_orders.append(order_info)
            
            # Check if it would be included
            if order_date_pr == target_date_only and order_state in ['locked', 'paid', 'open', 'completed']:
                included.append(order_info)
            else:
                filtered_out.append(order_info)
    
    return all_brookie_orders, included, filtered_out

def main():
    print("=" * 80)
    print("DEBUGGING VSJ BROOKIE ORDERS")
    print("Clover site: 123")
    print("Our API: 96")
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
    start_date = target_date - timedelta(days=1)
    end_date = target_date + timedelta(days=1)
    
    print(f"\n[1/3] Fetching all orders from {start_date.date()} to {end_date.date()}...")
    all_orders = fetch_all_orders(vsj_creds, start_date, end_date)
    print(f"  Found {len(all_orders)} total orders")
    
    print(f"\n[2/3] Analyzing Brookie orders...")
    all_brookie, included, filtered = analyze_brookie_orders(all_orders, target_date)
    
    print(f"\n  Total Brookie orders found: {len(all_brookie)}")
    print(f"  Included (will be counted): {len(included)}")
    print(f"  Filtered out: {len(filtered)}")
    
    total_included = sum(o['brookie_count'] for o in included)
    total_filtered = sum(o['brookie_count'] for o in filtered)
    total_all = sum(o['brookie_count'] for o in all_brookie)
    
    print(f"\n  Brookie count - Included: {total_included}")
    print(f"  Brookie count - Filtered: {total_filtered}")
    print(f"  Brookie count - Total: {total_all}")
    
    print(f"\n[3/3] Filtered out orders (might explain missing 27):")
    print("=" * 80)
    
    # Group filtered orders by reason
    by_date = [o for o in filtered if not o['is_target_date']]
    by_state = [o for o in filtered if o['is_target_date'] and not o['will_process']]
    
    print(f"\nFiltered by date (not Feb 15): {len(by_date)} orders, {sum(o['brookie_count'] for o in by_date)} Brookie items")
    for o in by_date[:10]:  # Show first 10
        print(f"  Order {o['order_id']}: {o['brookie_count']} Brookie, Date: {o['date_pr']}, State: {o['state']}")
    
    print(f"\nFiltered by state (Feb 15 but wrong state): {len(by_state)} orders, {sum(o['brookie_count'] for o in by_state)} Brookie items")
    for o in by_state[:10]:  # Show first 10
        print(f"  Order {o['order_id']}: {o['brookie_count']} Brookie, State: {o['state']}")
    
    print("\n" + "=" * 80)
    print("ANALYSIS:")
    print(f"  Our API count: {total_included}")
    print(f"  Clover site count: 123")
    print(f"  Difference: {123 - total_included}")
    print(f"  Filtered out count: {total_filtered}")
    print("=" * 80)

if __name__ == "__main__":
    main()
