"""
Trace exactly what happens during processing to find where items are lost
"""

import sys
import codecs
from vm_inventory_updater_fixed import load_credentials, clean_cookie_name
from datetime import datetime as dt, timedelta
from zoneinfo import ZoneInfo
import requests

# Fix Unicode encoding
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def trace_processing(creds, target_date):
    """Trace processing step by step"""
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
    
    print(f"\n[1/5] Fetching orders...")
    response = requests.get(orders_url, params=params, timeout=60)
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
    
    # Process exactly like the main script
    print(f"\n[2/5] Processing items (matching main script logic)...")
    
    valid_states = ['locked', 'paid', 'open', 'completed']
    test_keywords = ['d:water', 'water', 'test', 'pick mini shots', 'shot glass', 'alcohol', 'don q', 'coco', 's:', 'x:', 'a:', ';;', '***', '...', 'empty']
    
    cookie_sales = {}  # Raw cookie sales before consolidation
    brookie_tracking = []  # Track all Brookie items
    
    for order in filtered_orders:
        order_state = order.get('state', '')
        if order_state not in valid_states:
            continue
        
        line_items_data = order.get('lineItems', {})
        line_items = line_items_data.get('elements', []) if isinstance(line_items_data, dict) else []
        
        for item in line_items:
            if not isinstance(item, dict):
                continue
            
            item_name = item.get('name', '')
            item_name_lower = item_name.lower()
            quantity = item.get('unitQty', 0) or item.get('quantity', 0) or 1
            
            # Test keywords filter
            if any(keyword in item_name_lower for keyword in test_keywords):
                continue
            
            # Check if cookie
            is_brookie = 'brookie' in item_name_lower and 'F' in item_name
            is_cookie = (
                is_brookie or
                'cookie' in item_name_lower or
                'chocolate' in item_name_lower or
                'cornbread' in item_name_lower or
                'cherry' in item_name_lower or
                'cake' in item_name_lower or
                'brownie' in item_name_lower or
                'nutella' in item_name_lower or
                'biscoff' in item_name_lower or
                'churro' in item_name_lower or
                'tres leches' in item_name_lower or
                'lemon' in item_name_lower or
                'strawberry' in item_name_lower or
                'white chocolate' in item_name_lower or
                'midnight' in item_name_lower or
                'pecan' in item_name_lower or
                'brûlée' in item_name_lower or
                'brulée' in item_name_lower or
                item_name.startswith('*')
            )
            
            if not is_cookie:
                continue
            
            # Track Brookie specifically
            if is_brookie:
                brookie_tracking.append({
                    'item_name': item_name,
                    'quantity': quantity,
                    'order_id': order.get('id', 'Unknown')
                })
            
            # Add to cookie_sales
            if item_name in cookie_sales:
                cookie_sales[item_name] += quantity
            else:
                cookie_sales[item_name] = quantity
    
    print(f"  Raw cookie_sales entries: {len(cookie_sales)}")
    print(f"  Total Brookie items tracked: {len(brookie_tracking)}")
    print(f"  Total Brookie quantity (raw): {sum(b['quantity'] for b in brookie_tracking)}")
    
    # Show unique Brookie item names
    print(f"\n[3/5] Unique Brookie item names found:")
    unique_brookie_names = {}
    for b in brookie_tracking:
        name = b['item_name']
        if name not in unique_brookie_names:
            unique_brookie_names[name] = {'count': 0, 'quantity': 0}
        unique_brookie_names[name]['count'] += 1
        unique_brookie_names[name]['quantity'] += b['quantity']
    
    for name, stats in sorted(unique_brookie_names.items()):
        print(f"  '{name}': {stats['quantity']} quantity ({stats['count']} items)")
    
    # Consolidation step
    print(f"\n[4/5] Consolidation step...")
    
    consolidated_sales = {}
    brookie_consolidation_tracking = []
    
    for cookie_name, sales_count in cookie_sales.items():
        cleaned_name = clean_cookie_name(cookie_name)
        
        # Track Brookie consolidation
        if 'brookie' in cookie_name.lower():
            brookie_consolidation_tracking.append({
                'original': cookie_name,
                'cleaned': cleaned_name,
                'quantity': sales_count
            })
        
        # Skip PICK Minishots
        if 'pick' in cleaned_name.lower() and 'minishot' in cleaned_name.lower():
            continue
        
        if cleaned_name in consolidated_sales:
            consolidated_sales[cleaned_name] += sales_count
        else:
            consolidated_sales[cleaned_name] = sales_count
    
    print(f"  Consolidated entries: {len(consolidated_sales)}")
    
    # Show Brookie consolidation details
    print(f"\n  Brookie consolidation details:")
    for track in brookie_consolidation_tracking:
        print(f"    '{track['original']}' ({track['quantity']}) -> '{track['cleaned']}'")
    
    final_brookie = consolidated_sales.get('F - Brookie', 0)
    print(f"\n  Final consolidated Brookie: {final_brookie}")
    
    # Check for other Brookie keys
    print(f"\n[5/5] Checking for other Brookie keys in consolidated_sales:")
    for key, value in consolidated_sales.items():
        if 'brookie' in key.lower():
            print(f"  '{key}': {value}")
    
    print(f"\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Raw Brookie quantity: {sum(b['quantity'] for b in brookie_tracking)}")
    print(f"Final consolidated Brookie: {final_brookie}")
    print(f"Difference: {sum(b['quantity'] for b in brookie_tracking) - final_brookie}")
    
    if sum(b['quantity'] for b in brookie_tracking) != final_brookie:
        print(f"\n[ISSUE FOUND] Items are being lost during consolidation!")
        print(f"  Check if clean_cookie_name is mapping Brookie items incorrectly")

def main():
    print("=" * 80)
    print("TRACING PROCESSING TO FIND LOST ITEMS")
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
    
    trace_processing(vsj_creds, target_date)

if __name__ == "__main__":
    main()
