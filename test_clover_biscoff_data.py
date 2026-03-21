#!/usr/bin/env python3
"""
Test Clover API to see what data it returns for Biscoff items
This will help us verify the mapping is working correctly
"""

import json
import requests
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Load Clover credentials
with open('clover_creds.json', 'r') as f:
    clover_creds = json.load(f)

merchant_id = clover_creds.get('merchant_id')
access_token = clover_creds.get('access_token')

if not merchant_id or not access_token:
    print("❌ Missing Clover credentials")
    sys.exit(1)

print("="*80)
print("TESTING CLOVER API FOR BISCOFF ITEMS")
print("="*80)

# Get yesterday's orders (most recent data)
tz = ZoneInfo("America/Puerto_Rico")
yesterday = datetime.now(tz) - timedelta(days=1)
start_time = int(yesterday.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
end_time = int(yesterday.replace(hour=23, minute=59, second=59, microsecond=999).timestamp() * 1000)

print(f"\nChecking orders from: {yesterday.strftime('%Y-%m-%d')}")
print(f"Time range: {start_time} to {end_time}")

# Get orders
url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}
params = {
    "filter": f"createdTime>={start_time}&createdTime<={end_time}",
    "expand": "lineItems"
}

try:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    orders_data = response.json()
    
    print(f"\n✅ Found {len(orders_data.get('elements', []))} orders")
    
    # Check for Biscoff items
    biscoff_items = []
    for order in orders_data.get('elements', []):
        line_items = order.get('lineItems', {}).get('elements', [])
        for item in line_items:
            item_name = item.get('name', '')
            if 'biscoff' in item_name.lower() or 'Biscoff' in item_name:
                biscoff_items.append({
                    'name': item_name,
                    'order_id': order.get('id'),
                    'created_time': order.get('createdTime'),
                    'quantity': item.get('quantity', 1)
                })
    
    print(f"\n📊 Found {len(biscoff_items)} Biscoff-related line items:")
    for i, item in enumerate(biscoff_items[:10], 1):  # Show first 10
        print(f"  {i}. '{item['name']}' (Order: {item['order_id'][:8]}..., Qty: {item['quantity']})")
    
    if len(biscoff_items) > 10:
        print(f"  ... and {len(biscoff_items) - 10} more")
    
    # Check what the clean_cookie_name function would return
    print("\n" + "="*80)
    print("TESTING CLEAN_COOKIE_NAME FUNCTION")
    print("="*80)
    
    # Import the function
    sys.path.insert(0, '.')
    from vm_inventory_updater_fixed import clean_cookie_name
    
    unique_names = set(item['name'] for item in biscoff_items)
    print(f"\nUnique Biscoff item names from Clover API:")
    for name in sorted(unique_names):
        cleaned = clean_cookie_name(name)
        status = "✅" if cleaned == "N - Cheesecake with Biscoff" else "❌"
        print(f"  {status} '{name}' -> '{cleaned}'")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    if biscoff_items:
        print(f"✅ Found {len(biscoff_items)} Biscoff items in Clover API")
        print("✅ Check above to see if mapping is correct")
    else:
        print("⚠️  No Biscoff items found in yesterday's orders")
        print("   This could mean:")
        print("   - No Biscoff items were sold yesterday")
        print("   - The date range needs adjustment")
        print("   - There's an issue with the API query")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
