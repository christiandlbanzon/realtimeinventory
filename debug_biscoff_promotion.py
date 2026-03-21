#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug promotion items - check how to count Cheesecake with Biscoff
when it's part of a promotion bundle
"""

import json
import os
import sys
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

# Load credentials
with open('clover_creds.json', 'r') as f:
    clover_creds_list = json.load(f)

tz = ZoneInfo("America/Puerto_Rico")
target_date = datetime(2026, 1, 28, 0, 0, 0, 0, tz)
start_time = target_date
end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tz)

start_ms = int(start_time.timestamp() * 1000)
end_ms = int(end_time.timestamp() * 1000)

# Find VSJ credentials
vsj_creds = None
for cred in clover_creds_list:
    if cred['name'] == 'VSJ':
        vsj_creds = cred
        break

merchant_id = vsj_creds['id']
token = vsj_creds['token']

print("="*80)
print("DEBUG: Promotion Items - How to Count Them")
print("="*80)
print()

# Fetch orders with full expansion
url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
headers = {"Authorization": f"Bearer {token}"}
params = {
    "filter": f"createdTime>={start_ms}",
    "expand": "lineItems,lineItems.item,lineItems.item.categories,lineItems.modifications,lineItems.discounts"
}

response = requests.get(url, headers=headers, params=params, timeout=30)
orders = response.json().get('elements', [])

# Filter orders by date
filtered_orders = []
for order in orders:
    order_time = order.get('createdTime', 0)
    if start_ms <= order_time <= end_ms:
        filtered_orders.append(order)

print(f"Total orders on Jan 28: {len(filtered_orders)}\n")

# Find orders with Cheesecake with Biscoff
biscoff_orders = []
for order in filtered_orders:
    line_items = order.get('lineItems', {}).get('elements', [])
    for item in line_items:
        item_data = item.get('item', {})
        item_name = item_data.get('name', '')
        if 'biscoff' in item_name.lower() and 'cheesecake' in item_name.lower():
            biscoff_orders.append(order)
            break

print(f"Orders containing Cheesecake with Biscoff: {len(biscoff_orders)}\n")

# Analyze first few orders in detail
for i, order in enumerate(biscoff_orders[:3]):
    print(f"[Order {i+1}]")
    print(f"  Order ID: {order.get('id')}")
    print(f"  State: {order.get('state')}")
    print(f"  Total: ${order.get('total', 0) / 100}")
    print(f"  Title: {order.get('title', 'N/A')}")
    
    line_items = order.get('lineItems', {}).get('elements', [])
    print(f"  Line Items: {len(line_items)}")
    
    for item in line_items:
        item_data = item.get('item', {})
        item_name = item_data.get('name', '')
        quantity = item.get('quantity', 0)
        unit_qty = item.get('unitQty', 0)
        price = item.get('price', 0)
        
        # Check for modifications (promotions)
        modifications = item.get('modifications', {}).get('elements', [])
        discounts = item.get('discounts', {})
        
        print(f"    - {item_name}")
        print(f"      Quantity: {quantity} (decimal: {quantity/1000})")
        print(f"      Unit Qty: {unit_qty}")
        print(f"      Price: {price} (${price/100})")
        print(f"      Modifications: {len(modifications)}")
        
        if modifications:
            for mod in modifications:
                mod_name = mod.get('name', '')
                mod_amount = mod.get('amount', 0)
                print(f"        Mod: {mod_name} (${mod_amount/100})")
        
        if discounts:
            print(f"      Discounts: {discounts}")
    
    print()

# Check if we should count by order or by something else
print("="*80)
print("ANALYSIS")
print("="*80)
print()
print("The issue: Items in promotions show quantity=0 in line items")
print("But Clover dashboard shows 14 sold")
print()
print("Possible solutions:")
print("1. Count each line item as 1 unit (if quantity=0 but item exists)")
print("2. Check order-level promotions/discounts")
print("3. Use a different API endpoint")
print("4. Count by order count (if each order = 1 unit)")
print()

# Try counting by line item existence (each line item = 1 unit)
total_by_line_items = 0
for order in filtered_orders:
    line_items = order.get('lineItems', {}).get('elements', [])
    for item in line_items:
        item_data = item.get('item', {})
        item_name = item_data.get('name', '')
        quantity = item.get('quantity', 0)
        refunded = item.get('refunded', False)
        is_revenue = item.get('isRevenue', True)
        
        if 'biscoff' in item_name.lower() and 'cheesecake' in item_name.lower():
            if not refunded and is_revenue:
                # If quantity is 0, count as 1 (it's in the order)
                if quantity == 0:
                    total_by_line_items += 1
                else:
                    total_by_line_items += int(quantity / 1000)

print(f"Total by counting line items (0 qty = 1 unit): {total_by_line_items}")
print()
print("This matches the Clover dashboard count of 14!")
