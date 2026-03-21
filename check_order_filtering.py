"""Check if orders are being filtered out by has_real_cookies check"""

import os
import sys
import codecs
os.environ['FOR_DATE'] = '2026-02-15'

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from vm_inventory_updater_fixed import load_credentials
from datetime import datetime as dt, timedelta
from zoneinfo import ZoneInfo
import requests

creds_result = load_credentials()
clover_creds, _ = creds_result if isinstance(creds_result, tuple) else (creds_result, None)
vsj_creds = clover_creds.get('VSJ')

tz = ZoneInfo('America/Puerto_Rico')
target_date = dt(2026, 2, 15, 0, 0, 0, 0, tz)

start_time = dt(target_date.year, target_date.month, target_date.day, 0, 0, 0, 0, tz)
end_time = dt(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tz)

start_ms = int(start_time.timestamp() * 1000)
end_ms = int(end_time.timestamp() * 1000)
extended_start_ms = start_ms - (8 * 60 * 60 * 1000)

merchant_id = vsj_creds.get('id')
token = vsj_creds.get('token')

orders_url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
params = {
    'access_token': token,
    'filter': f'createdTime>={extended_start_ms}',
    'expand': 'lineItems',
    'limit': 1000
}

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

print(f"Total orders on Feb 15: {len(filtered_orders)}")

# Check has_real_cookies logic
valid_states = ['locked', 'paid', 'open', 'completed']
cookie_keywords = ['cookie', 'chocolate', 'nutella', 'cheesecake', 'churro', 'tres leches', 'fudge', 's\'mores', 'cinnamon', 'lemon', 'strawberry', 'pecan', 'guava', 'macadamia', 'biscoff']

orders_with_brookie = []
orders_skipped_no_cookies = []
orders_processed = []

for order in filtered_orders:
    order_state = order.get('state', '')
    order_id = order.get('id', 'Unknown')
    
    if order_state not in valid_states:
        continue
    
    line_items = order.get('lineItems', {}).get('elements', [])
    
    # Check if order has Brookie
    has_brookie = False
    for item in line_items:
        if isinstance(item, dict):
            item_name = item.get('name', '')
            item_name_lower = item_name.lower()
            if 'brookie' in item_name_lower and 'F' in item_name:
                has_brookie = True
                break
    
    if has_brookie:
        orders_with_brookie.append(order_id)
        
        # Check has_real_cookies
        has_real_cookies = False
        for item in line_items:
            item_name = item.get('name', '').lower()
            if any(keyword in item_name for keyword in cookie_keywords):
                has_real_cookies = True
                break
        
        if not has_real_cookies:
            orders_skipped_no_cookies.append({
                'order_id': order_id,
                'items': [item.get('name', '') for item in line_items if isinstance(item, dict)]
            })
        else:
            orders_processed.append(order_id)

print(f"\nOrders with Brookie: {len(orders_with_brookie)}")
print(f"Orders skipped (no real cookies): {len(orders_skipped_no_cookies)}")
print(f"Orders processed: {len(orders_processed)}")

if orders_skipped_no_cookies:
    print(f"\n[ISSUE FOUND] Orders with Brookie being skipped:")
    for order_info in orders_skipped_no_cookies[:10]:
        print(f"  Order {order_info['order_id']}: {order_info['items']}")
