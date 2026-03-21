#!/usr/bin/env python3
"""
Debug script to check why January 17 data isn't being fetched
"""

import os
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# Load credentials
with open("clover_creds.json") as f:
    clover_creds_list = json.load(f)

tz = ZoneInfo("America/Puerto_Rico")
target_date = datetime(2026, 1, 17, 0, 0, 0, 0, tz)

# Calculate time range
start_time = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, 0, target_date.tzinfo)
end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, target_date.tzinfo)

start_ms = int(start_time.timestamp() * 1000)
end_ms = int(end_time.timestamp() * 1000)

extended_start_ms = start_ms - (8 * 60 * 60 * 1000)
extended_end_ms = end_ms + (4 * 60 * 60 * 1000)

print("=" * 80)
print("DEBUGGING JANUARY 17 API QUERY")
print("=" * 80)
print(f"Target date: {target_date.strftime('%Y-%m-%d')}")
print(f"Start time (AST): {start_time}")
print(f"End time (AST): {end_time}")
print(f"Start ms: {start_ms}")
print(f"End ms: {end_ms}")
print(f"Extended start ms: {extended_start_ms}")
print(f"Extended end ms: {extended_end_ms}")
print()

# Test each store
for creds_data in clover_creds_list:
    if isinstance(creds_data, dict) and 'name' in creds_data:
        store_name = creds_data['name']
        merchant_id = creds_data.get('id')
        token = creds_data.get('token')
        
        if not merchant_id or not token:
            print(f"⚠️ Skipping {store_name}: missing credentials")
            continue
        
        print(f"\n{'='*80}")
        print(f"Testing store: {store_name}")
        print(f"{'='*80}")
        
        orders_url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
        params = {
            'access_token': token,
            'filter': f'createdTime>={extended_start_ms}&createdTime<={extended_end_ms}',  # Add upper bound
            'expand': 'lineItems',
            'limit': 1000
        }
        
        try:
            response = requests.get(orders_url, params=params, timeout=60)
            print(f"API Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                orders = data.get('elements', [])
                print(f"Total orders fetched: {len(orders)}")
                
                # Filter by date
                filtered = []
                for order in orders:
                    created_time = order.get('createdTime', 0)
                    if start_ms <= created_time <= end_ms:
                        order_state = order.get('state', '')
                        if order_state in ['locked', 'paid', 'open', 'completed']:
                            filtered.append(order)
                
                print(f"Orders in date range ({start_ms} to {end_ms}): {len(filtered)}")
                
                # Check for cookie items
                cookie_count = 0
                for order in filtered:
                    line_items_data = order.get('lineItems', {})
                    line_items = line_items_data.get('elements', []) if isinstance(line_items_data, dict) else []
                    for item in line_items:
                        item_name = item.get('name', '').lower()
                        if any(kw in item_name for kw in ['cookie', 'brookie', 'brownie', 'cornbread', 'cherry', 'cake', 'biscoff']):
                            quantity = item.get('unitQty', 0) or item.get('quantity', 0) or 1
                            cookie_count += quantity
                            print(f"  Found cookie item: {item.get('name')} (qty: {quantity})")
                
                print(f"Total cookie items found: {cookie_count}")
                
                if len(filtered) == 0:
                    print(f"\n⚠️ NO ORDERS FOUND for {store_name} on Jan 17!")
                    print(f"   Checking if orders exist outside date range...")
                    outside_count = 0
                    sample_times = []
                    for order in orders[:10]:  # Check first 10 orders
                        created_time = order.get('createdTime', 0)
                        if created_time:
                            from datetime import datetime as dt
                            order_dt = dt.fromtimestamp(created_time / 1000, tz=tz)
                            sample_times.append((created_time, order_dt.strftime('%Y-%m-%d %H:%M:%S %Z')))
                    print(f"   Sample order timestamps:")
                    for ts_ms, dt_str in sample_times[:5]:
                        print(f"     {ts_ms} = {dt_str}")
                    print(f"   Expected range: {start_ms} ({start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}) to {end_ms} ({end_time.strftime('%Y-%m-%d %H:%M:%S %Z')})")
                    
            else:
                print(f"❌ API Error: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
