#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug why Cheesecake with Biscoff (N) is showing 0 on Jan 28
when Clover shows 14 sold at VSJ (Old San Juan)
"""

import json
import os
import sys
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

print("="*80)
print("DEBUG: Cheesecake with Biscoff - January 28, 2026")
print("="*80)
print()

# Load credentials
with open('clover_creds.json', 'r') as f:
    clover_creds_list = json.load(f)

tz = ZoneInfo("America/Puerto_Rico")
target_date = datetime(2026, 1, 28, 0, 0, 0, 0, tz)
start_time = target_date
end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tz)

start_ms = int(start_time.timestamp() * 1000)
end_ms = int(end_time.timestamp() * 1000)

print(f"Target Date: {target_date.strftime('%B %d, %Y')}")
print(f"Time Range: {start_ms} to {end_ms}")
print()

# Find VSJ credentials
vsj_creds = None
for cred in clover_creds_list:
    if cred['name'] == 'VSJ':
        vsj_creds = cred
        break

if not vsj_creds:
    print("ERROR: VSJ credentials not found")
    sys.exit(1)

print(f"VSJ Credentials:")
print(f"  Merchant ID: {vsj_creds['id']}")
print(f"  Category ID: {vsj_creds['cookie_category_id']}")
print()

# Fetch orders from VSJ
merchant_id = vsj_creds['id']
token = vsj_creds['token']
category_id = vsj_creds['cookie_category_id']

print("[1] Fetching orders from Clover API...")
url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
headers = {"Authorization": f"Bearer {token}"}
params = {
    "filter": f"createdTime>={start_ms}",
    "expand": "lineItems,lineItems.item,lineItems.item.categories"
}

try:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    
    if response.status_code != 200:
        print(f"ERROR: API returned status {response.status_code}")
        print(f"Response: {response.text[:500]}")
        sys.exit(1)
    
    orders_data = response.json()
    orders = orders_data.get('elements', [])
    
    print(f"  Found {len(orders)} total orders")
    
    # Filter orders by date
    filtered_orders = []
    for order in orders:
        order_time = order.get('createdTime', 0)
        if start_ms <= order_time <= end_ms:
            filtered_orders.append(order)
    
    print(f"  Orders on Jan 28: {len(filtered_orders)}")
    print()
    
    # Look for Cheesecake with Biscoff
    print("[2] Searching for Cheesecake with Biscoff...")
    biscoff_items = []
    biscoff_count = 0
    
    for order in filtered_orders:
        order_id = order.get('id', '')
        line_items = order.get('lineItems', {}).get('elements', [])
        
        for item in line_items:
            item_data = item.get('item', {})
            item_name = item_data.get('name', '')
            quantity = item.get('quantity', 0)
            refunded = item.get('refunded', False)
            is_revenue = item.get('isRevenue', True)
            
            # Check if it's Cheesecake with Biscoff
            if 'biscoff' in item_name.lower() and 'cheesecake' in item_name.lower():
                qty_decimal = quantity / 1000  # Clover uses millis
                
                # Check categories
                categories = item_data.get('categories', {}).get('elements', [])
                is_in_cookie_category = any(cat.get('id') == category_id for cat in categories)
                
                biscoff_items.append({
                    'order_id': order_id,
                    'item_name': item_name,
                    'quantity': quantity,
                    'quantity_decimal': qty_decimal,
                    'refunded': refunded,
                    'is_revenue': is_revenue,
                    'in_cookie_category': is_in_cookie_category,
                    'categories': [cat.get('name', '') for cat in categories]
                })
                
                if not refunded and is_revenue:
                    biscoff_count += qty_decimal
    
    print(f"  Found {len(biscoff_items)} Cheesecake with Biscoff line items")
    print(f"  Total sold (non-refunded, revenue): {int(biscoff_count)}")
    print()
    
    if biscoff_items:
        print("[3] Detailed item breakdown:")
        for item in biscoff_items:
            print(f"  Order: {item['order_id']}")
            print(f"    Item Name: {item['item_name']}")
            print(f"    Quantity: {item['quantity']} ({item['quantity_decimal']})")
            print(f"    Refunded: {item['refunded']}")
            print(f"    Is Revenue: {item['is_revenue']}")
            print(f"    In Cookie Category: {item['in_cookie_category']}")
            print(f"    Categories: {', '.join(item['categories'])}")
            print()
    
    # Test cookie name cleaning
    print("[4] Testing cookie name mapping...")
    if biscoff_items:
        api_name = biscoff_items[0]['item_name']
        print(f"  API Name: '{api_name}'")
        
        # Simulate the clean_cookie_name function
        cleaned = api_name.strip()
        
        # Check if it starts with *N*
        if cleaned.startswith('*N*'):
            print(f"  ✓ Detected *N* prefix")
            # Remove prefix
            cleaned = cleaned.replace('*N*', '').strip()
            print(f"  After removing *N*: '{cleaned}'")
        
        # Remove special characters
        special_chars = ['☆', '✩', '®', '™']
        for char in special_chars:
            cleaned = cleaned.replace(char, '')
        
        print(f"  After cleaning: '{cleaned}'")
        
        # Expected sheet name
        expected_sheet_name = "N - Cheesecake with Biscoff"
        print(f"  Expected Sheet Name: '{expected_sheet_name}'")
        
        if cleaned.lower() == expected_sheet_name.lower().replace('n - ', ''):
            print(f"  ✓ Name matches!")
        else:
            print(f"  ⚠️  Name might not match correctly")
    
    print()
    
    # Check Google Sheet
    print("[5] Checking Google Sheet...")
    try:
        creds = Credentials.from_service_account_file(
            'service-account-key.json',
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=creds)
        
        # Try to find the sheet ID
        sheet_id = os.getenv('INVENTORY_SHEET_ID', '1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE')
        tab_name = "1-28"
        
        print(f"  Sheet ID: {sheet_id}")
        print(f"  Tab: {tab_name}")
        
        # Read row 16 (Cheesecake with Biscoff)
        range_name = f"{tab_name}!A16:BW16"
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if values and len(values) > 0:
            row = values[0]
            cookie_name = row[0] if len(row) > 0 else ""
            print(f"  Row 16 Cookie Name: '{cookie_name}'")
            
            # Find Old San Juan column (BU)
            # Based on the image, Old San Juan "Live Sales Data" is column BU
            # Column BU is index 72 (A=0, B=1, ..., BU=72)
            if len(row) > 72:
                osj_live_sales = row[72] if len(row) > 72 else "0"
                print(f"  Old San Juan Live Sales Data (BU16): {osj_live_sales}")
            else:
                print(f"  ⚠️  Row doesn't have enough columns")
        else:
            print(f"  ⚠️  Could not read row 16")
            
    except Exception as e:
        print(f"  ERROR checking sheet: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("="*80)
    print("DIAGNOSIS")
    print("="*80)
    
    if biscoff_count == 14:
        print("✅ Clover API shows 14 sold (matches dashboard)")
    else:
        print(f"⚠️  Clover API shows {int(biscoff_count)} sold (expected 14)")
    
    print("\nPossible Issues:")
    print("1. Cookie name mapping: *N* Cheesecake with Biscoff → N - Cheesecake with Biscoff")
    print("2. Location mapping: VSJ → Old San Juan")
    print("3. Column detection: Old San Juan 'Live Sales Data' column (BU)")
    print("4. Category filtering: Item must be in cookie category")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
