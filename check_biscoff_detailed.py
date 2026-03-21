#!/usr/bin/env python3
"""
Check Cheesecake with Biscoff items in detail to see why quantity is 0
"""
import os
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

# Load credentials
with open('clover_creds.json', 'r') as f:
    clover_creds_list = json.load(f)

tz = ZoneInfo("America/Puerto_Rico")
target_date = datetime(2026, 1, 27, 0, 0, 0, 0, tz)
start_time = target_date
end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tz)

start_ms = int(start_time.timestamp() * 1000)
end_ms = int(end_time.timestamp() * 1000)

print("="*80)
print(f"DETAILED CHECK: CHEESECAKE WITH BISCOFF")
print(f"Date: {target_date.strftime('%B %d, %Y')}")
print("="*80)
print()

# Focus on San Patricio since that's what the user mentioned
for creds in clover_creds_list:
    location_name = creds.get('name', 'Unknown')
    
    # Only check San Patricio for now
    if 'San Patricio' not in location_name:
        continue
    
    merchant_id = creds.get('id')
    token = creds.get('token')
    
    if not all([merchant_id, token]):
        continue
    
    print(f"\n{location_name}:")
    print("-" * 60)
    
    url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
    params = {
        'access_token': token,
        'filter': f'createdTime>={start_ms}',
        'expand': 'lineItems',
        'limit': 1000
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            print(f"  ERROR: API returned status {response.status_code}")
            continue
        
        orders_data = response.json()
        orders = orders_data.get('elements', [])
        
        # Filter orders by date
        filtered_orders = []
        for order in orders:
            order_time = order.get('createdTime', 0)
            if start_ms <= order_time <= end_ms:
                order_state = order.get('state', '')
                if order_state in ['locked', 'paid', 'open', 'completed']:
                    filtered_orders.append(order)
        
        print(f"  Total orders: {len(filtered_orders)}")
        
        # Look for Cheesecake with Biscoff in detail
        biscoff_count = 0
        biscoff_details = []
        
        for order in filtered_orders:
            order_id = order.get('id', '')
            order_state = order.get('state', '')
            line_items = order.get('lineItems', {}).get('elements', [])
            
            for item in line_items:
                item_name = item.get('name', '')
                quantity = item.get('quantity', 0)
                price = item.get('price', 0)
                unit_qty = item.get('unitQty', 0)
                refunded = item.get('refunded', False)
                is_revenue = item.get('isRevenue', True)
                
                # Check for Biscoff
                if '*N*' in item_name and 'cheesecake' in item_name.lower() and 'biscoff' in item_name.lower():
                    qty_decimal = quantity / 1000  # Clover uses millis
                    biscoff_details.append({
                        'order_id': order_id,
                        'order_state': order_state,
                        'item_name': item_name,
                        'quantity': quantity,
                        'quantity_decimal': qty_decimal,
                        'unit_qty': unit_qty,
                        'price': price,
                        'refunded': refunded,
                        'is_revenue': is_revenue,
                        'full_item': item
                    })
                    if not refunded and is_revenue:
                        biscoff_count += qty_decimal
        
        print(f"\n  Found {len(biscoff_details)} Cheesecake with Biscoff line items:")
        for detail in biscoff_details:
            print(f"\n    Order: {detail['order_id']} (State: {detail['order_state']})")
            print(f"      Item: {detail['item_name']}")
            print(f"      Quantity (raw): {detail['quantity']}")
            print(f"      Quantity (decimal): {detail['quantity_decimal']}")
            print(f"      Unit Qty: {detail['unit_qty']}")
            print(f"      Price: {detail['price']}")
            print(f"      Refunded: {detail['refunded']}")
            print(f"      Is Revenue: {detail['is_revenue']}")
        
        print(f"\n  TOTAL (non-refunded, revenue items): {int(biscoff_count)}")
        
        if biscoff_count == 0 and len(biscoff_details) > 0:
            print(f"\n  ⚠️ WARNING: Found items but all have 0 quantity or are refunded!")
            print(f"  This explains why the VM script sets it to 0.")
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)
print("If Clover API shows 0 quantity for all items, the VM script will")
print("correctly set the sheet to 0. If you manually set it to 3, the")
print("VM script will overwrite it back to 0 on the next run (every 5 min).")
print("\nOptions:")
print("1. Fix the data in Clover (if the sales actually happened)")
print("2. Temporarily disable VM updates for this item")
print("3. Manually update after VM runs (not recommended)")
