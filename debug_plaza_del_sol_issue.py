#!/usr/bin/env python3
"""
Debug script to trace why Plaza Del Sol Cookies & Cream shows 1 instead of 14
"""

import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

# Import functions from vm_inventory_updater
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# We'll need to import the functions, but let's recreate the key parts for debugging
from vm_inventory_updater import fetch_clover_sales, clean_cookie_name, find_cookie_row

# Get yesterday's date (January 24, 2026)
tz = ZoneInfo("America/Puerto_Rico")
today = datetime.now(tz)
yesterday = today - timedelta(days=1)
TARGET_DATE = yesterday

print("="*80)
print(f"DEBUGGING PLAZA DEL SOL COOKIES & CREAM ISSUE")
print(f"Date: {TARGET_DATE.strftime('%Y-%m-%d')}")
print("="*80)
print()

# Load Clover credentials
with open("clover_creds.json", "r") as f:
    clover_creds_list = json.load(f)

# Find PlazaSol credentials
plazasol_creds = None
for cred in clover_creds_list:
    if cred['name'] == 'PlazaSol':
        plazasol_creds = cred
        break

if not plazasol_creds:
    print("ERROR: PlazaSol credentials not found")
    exit(1)

print(f"[1/5] Fetching raw API data for PlazaSol...")
print(f"  Merchant ID: {plazasol_creds['id']}")
print()

# Fetch orders directly to see raw data
merchant_id = plazasol_creds['id']
token = plazasol_creds['token']
cookie_category_id = plazasol_creds['cookie_category_id']

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

print(f"[2/5] Analyzing raw cookie data from API...")
raw_cookie_counts = {}
cookies_cream_items = []

for order in filtered_orders:
    line_items_data = order.get('lineItems', {})
    line_items = line_items_data.get('elements', [])
    
    for item in line_items:
        item_name = item.get('name', '')
        item_name_lower = item_name.lower()
        
        # Skip test items
        test_keywords = [
            'd:water', 'water', 'test', 'pick mini shots', 'shot glass', 'alcohol',
            'don q', 'coco', 's:', 'x:', 'a:', ';;', '***', '...', 'empty'
        ]
        
        if any(keyword in item_name_lower for keyword in test_keywords):
            continue
        
        # Count raw items
        if item_name not in raw_cookie_counts:
            raw_cookie_counts[item_name] = 0
        
        raw_cookie_counts[item_name] += 1
        
        # Track Cookies & Cream specifically
        if 'cookies' in item_name_lower and 'cream' in item_name_lower:
            cookies_cream_items.append({
                'name': item_name,
                'order_id': order.get('id', 'Unknown'),
                'order_time': order.get('createdTime', 0)
            })

print(f"  Found {len(raw_cookie_counts)} unique cookie names")
print(f"  Found {len(cookies_cream_items)} Cookies & Cream items")
print()

print("Cookies & Cream items found:")
for item in cookies_cream_items[:20]:  # Show first 20
    safe_name = item['name'].encode('ascii', 'ignore').decode('ascii')
    print(f"  '{safe_name}' (Order: {item['order_id']})")

if len(cookies_cream_items) > 20:
    print(f"  ... and {len(cookies_cream_items) - 20} more")

print()
print("All raw cookie counts:")
for cookie_name, count in sorted(raw_cookie_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
    safe_name = cookie_name.encode('ascii', 'ignore').decode('ascii')
    print(f"  {safe_name}: {count}")

print()

print(f"[3/5] Testing clean_cookie_name function...")
cleaned_counts = {}
for cookie_name, count in raw_cookie_counts.items():
    cleaned = clean_cookie_name(cookie_name)
    if cleaned:
        if cleaned not in cleaned_counts:
            cleaned_counts[cleaned] = []
        cleaned_counts[cleaned].append((cookie_name, count))

print(f"  After cleaning: {len(cleaned_counts)} unique cleaned names")
print()

# Find Cookies & Cream in cleaned data
cookies_cream_cleaned = {}
for cleaned_name, items in cleaned_counts.items():
    if 'cookies' in cleaned_name.lower() and 'cream' in cleaned_name.lower():
        cookies_cream_cleaned[cleaned_name] = items

print("Cookies & Cream after cleaning:")
for cleaned_name, items in cookies_cream_cleaned.items():
    total = sum(count for _, count in items)
    print(f"  '{cleaned_name}': {total} total")
    for orig_name, count in items:
        safe_orig = orig_name.encode('ascii', 'ignore').decode('ascii')
        print(f"    - '{safe_orig}': {count}")

print()

print(f"[4/5] Testing fetch_clover_sales function...")
sales_data = fetch_clover_sales(plazasol_creds, TARGET_DATE)

print(f"  Function returned {len(sales_data)} cookie types")
print()

# Find Cookies & Cream in sales_data
cookies_cream_in_sales = {}
for cookie_name, count in sales_data.items():
    if 'cookies' in cookie_name.lower() and 'cream' in cookie_name.lower():
        cookies_cream_in_sales[cookie_name] = count

print("Cookies & Cream in sales_data:")
for cookie_name, count in cookies_cream_in_sales.items():
    print(f"  '{cookie_name}': {count}")

if not cookies_cream_in_sales:
    print("  WARNING: No Cookies & Cream found in sales_data!")
    print("  All cookies in sales_data:")
    for cookie_name, count in sales_data.items():
        safe_name = cookie_name.encode('ascii', 'ignore').decode('ascii')
        print(f"    '{safe_name}': {count}")

print()

print(f"[5/5] Testing find_cookie_row function...")
# Mock cookie names from sheet
mock_cookie_names = [
    "A - Chocolate Chip Nutella",
    "B - Signature Chocolate Chip",
    "C - Cookies & Cream",
    "D - White Chocolate Macadamia",
    # ... etc
]

if cookies_cream_in_sales:
    for cookie_name, count in cookies_cream_in_sales.items():
        row = find_cookie_row(mock_cookie_names, cookie_name)
        print(f"  '{cookie_name}' (count: {count}) -> row {row}")
        if row is None:
            print(f"    ERROR: Could not find row for '{cookie_name}'")
            print(f"    Available cookie names: {mock_cookie_names[:5]}...")
else:
    print("  No Cookies & Cream data to test row finding")

print()
print("="*80)
print("SUMMARY")
print("="*80)
print(f"Raw API Cookies & Cream items: {len(cookies_cream_items)}")
if cookies_cream_cleaned:
    total_cleaned = sum(sum(count for _, count in items) for items in cookies_cream_cleaned.values())
    print(f"After cleaning: {total_cleaned}")
else:
    print("After cleaning: 0 (no matches)")
if cookies_cream_in_sales:
    total_sales = sum(cookies_cream_in_sales.values())
    print(f"In sales_data: {total_sales}")
else:
    print("In sales_data: 0 (not found)")
print("="*80)
