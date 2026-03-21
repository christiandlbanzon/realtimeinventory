#!/usr/bin/env python3
"""
Detailed analysis of cookie names from Clover API for VSJ
to identify why Cookies & Cream shows 490 instead of 100
"""

import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

# Get yesterday's date (January 24, 2026)
tz = ZoneInfo("America/Puerto_Rico")
today = datetime.now(tz)
yesterday = today - timedelta(days=1)
TARGET_DATE = yesterday

print("="*80)
print(f"DETAILED COOKIE ANALYSIS FOR VSJ - {TARGET_DATE.strftime('%Y-%m-%d')}")
print("="*80)
print()

# Load Clover credentials
with open("clover_creds.json", "r") as f:
    clover_creds_list = json.load(f)

# Find VSJ credentials
vsj_creds = None
for cred in clover_creds_list:
    if cred['name'] == 'VSJ':
        vsj_creds = cred
        break

if not vsj_creds:
    print("ERROR: VSJ credentials not found")
    exit(1)

merchant_id = vsj_creds['id']
token = vsj_creds['token']
cookie_category_id = vsj_creds['cookie_category_id']

# Fetch orders
start_time = datetime(TARGET_DATE.year, TARGET_DATE.month, TARGET_DATE.day, 0, 0, 0, 0, tz)
end_time = datetime(TARGET_DATE.year, TARGET_DATE.month, TARGET_DATE.day, 23, 59, 59, 999999, tz)

start_ms = int(start_time.timestamp() * 1000)
end_ms = int(end_time.timestamp() * 1000)

url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
params = {
    'access_token': token,
    'filter': f'createdTime>={start_ms}',
    'expand': 'lineItems',
    'limit': 1000
}

print(f"[1/3] Fetching orders from Clover API...")
all_orders = []
offset = 0
limit = 100

while True:
    params_with_limit = {**params, "limit": limit, "offset": offset}
    response = requests.get(url, params=params_with_limit, timeout=60)
    
    if response.status_code != 200:
        print(f"  ERROR: API returned status {response.status_code}")
        break
    
    data = response.json()
    orders = data.get("elements", [])
    
    if not orders:
        break
    
    all_orders.extend(orders)
    
    if len(orders) < limit:
        break
    
    offset += limit

print(f"  Found {len(all_orders)} total orders")

# Filter orders by date
filtered_orders = []
for order in all_orders:
    created_time = order.get("createdTime", 0)
    if start_ms <= created_time <= end_ms:
        order_state = order.get('state', '')
        if order_state in ['locked', 'paid', 'open', 'completed']:
            filtered_orders.append(order)

print(f"  Filtered to {len(filtered_orders)} orders within date range")
print()

# Analyze all cookie names
print(f"[2/3] Analyzing all cookie names...")
cookie_details = {}

for order in filtered_orders:
    line_items_data = order.get('lineItems', {})
    line_items = line_items_data.get('elements', [])
    
    for item in line_items:
        item_name = item.get('name', '')
        
        # Skip test items
        test_keywords = ['d:water', 'water', 'test', 'pick mini shots', 'shot glass', 'alcohol']
        if any(keyword in item_name.lower() for keyword in test_keywords):
            continue
        
        # Count each occurrence
        if item_name not in cookie_details:
            cookie_details[item_name] = {
                'count': 0,
                'orders': []
            }
        
        cookie_details[item_name]['count'] += 1
        cookie_details[item_name]['orders'].append(order.get('id', 'Unknown'))

print(f"  Found {len(cookie_details)} unique cookie names")
print()

# Focus on Cookies & Cream variations
print(f"[3/3] Cookies & Cream Analysis:")
print("="*80)

cookies_cream_total = 0
cookies_cream_variations = {}

for cookie_name, details in cookie_details.items():
    cookie_lower = cookie_name.lower()
    
    # Check if this is a Cookies & Cream variation
    if 'cookies' in cookie_lower and 'cream' in cookie_lower:
        cookies_cream_variations[cookie_name] = details['count']
        cookies_cream_total += details['count']
        # Handle Unicode characters safely
        safe_name = cookie_name.encode('ascii', 'ignore').decode('ascii')
        print(f"  '{safe_name}': {details['count']} units")

print()
print("="*80)
print(f"TOTAL Cookies & Cream (all variations): {cookies_cream_total}")
print("="*80)
print()

# Show all cookie names for reference
print("All cookie names found:")
print("-"*80)
for cookie_name, details in sorted(cookie_details.items(), key=lambda x: x[1]['count'], reverse=True):
    safe_name = cookie_name.encode('ascii', 'ignore').decode('ascii')
    print(f"  {safe_name}: {details['count']} units")
