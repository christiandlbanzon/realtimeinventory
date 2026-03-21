#!/usr/bin/env python3
"""
Simple debug script to trace Plaza Del Sol Cookies & Cream issue
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
print(f"DEBUGGING PLAZA DEL SOL COOKIES & CREAM")
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

merchant_id = plazasol_creds['id']
token = plazasol_creds['token']

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

print("[1] Fetching orders from API...")
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

print("[2] Analyzing Cookies & Cream items...")
cookies_cream_raw = {}

for order in filtered_orders:
    line_items_data = order.get('lineItems', {})
    line_items = line_items_data.get('elements', [])
    
    for item in line_items:
        item_name = item.get('name', '')
        item_name_lower = item_name.lower()
        
        # Skip test items (same logic as vm_inventory_updater.py)
        test_keywords = [
            'd:water', 'water', 'test', 'pick mini shots', 'shot glass', 'alcohol',
            'don q', 'coco', 's:', 'x:', 'a:', ';;', '***', '...', 'empty'
        ]
        
        if any(keyword in item_name_lower for keyword in test_keywords):
            continue
        
        # Check if this is Cookies & Cream
        if 'cookies' in item_name_lower and 'cream' in item_name_lower:
            if item_name not in cookies_cream_raw:
                cookies_cream_raw[item_name] = 0
            cookies_cream_raw[item_name] += 1

print(f"  Found {sum(cookies_cream_raw.values())} total Cookies & Cream items")
print()

print("Raw Cookies & Cream items:")
for name, count in cookies_cream_raw.items():
    safe_name = name.encode('ascii', 'ignore').decode('ascii')
    print(f"  '{safe_name}': {count}")

print()

print("[3] Testing clean_cookie_name function...")
# Import clean_cookie_name from vm_inventory_updater
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Read the clean_cookie_name function
from vm_inventory_updater import clean_cookie_name

cleaned_counts = {}
for cookie_name, count in cookies_cream_raw.items():
    cleaned = clean_cookie_name(cookie_name)
    print(f"  '{cookie_name.encode('ascii', 'ignore').decode('ascii')}' -> '{cleaned}'")
    
    if cleaned:
        if cleaned not in cleaned_counts:
            cleaned_counts[cleaned] = 0
        cleaned_counts[cleaned] += count

print()
print("After cleaning:")
for cleaned_name, total_count in cleaned_counts.items():
    print(f"  '{cleaned_name}': {total_count}")

print()

print("[4] Testing fetch_clover_sales function...")
# Temporarily disable logging to avoid Unicode errors
import logging
import io
import sys

# Redirect stderr to suppress Unicode errors
old_stderr = sys.stderr
sys.stderr = io.StringIO()

logging.disable(logging.CRITICAL)

from vm_inventory_updater import fetch_clover_sales

sales_data = fetch_clover_sales(plazasol_creds, TARGET_DATE)

logging.disable(logging.NOTSET)
sys.stderr = old_stderr

print(f"  Function returned {len(sales_data)} cookie types")
print()

# Find Cookies & Cream in sales_data
cookies_cream_in_sales = {}
for cookie_name, count in sales_data.items():
    if 'cookies' in cookie_name.lower() and 'cream' in cookie_name.lower():
        cookies_cream_in_sales[cookie_name] = count

print("Cookies & Cream in sales_data:")
if cookies_cream_in_sales:
    for cookie_name, count in cookies_cream_in_sales.items():
        print(f"  '{cookie_name}': {count}")
else:
    print("  WARNING: No Cookies & Cream found!")
    print("  All cookies returned:")
    for cookie_name, count in list(sales_data.items())[:10]:
        safe_name = cookie_name.encode('ascii', 'ignore').decode('ascii')
        print(f"    '{safe_name}': {count}")

print()
print("="*80)
print("SUMMARY")
print("="*80)
print(f"Raw API Cookies & Cream items: {sum(cookies_cream_raw.values())}")
print(f"After cleaning: {sum(cleaned_counts.values())}")
if cookies_cream_in_sales:
    print(f"In sales_data: {sum(cookies_cream_in_sales.values())}")
else:
    print(f"In sales_data: 0 (NOT FOUND!)")
print("="*80)
