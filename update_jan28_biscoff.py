#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manually update January 28 Cheesecake with Biscoff data
Fetches correct count from Clover API and updates Google Sheet
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

def fetch_vsj_biscoff_jan28():
    """Fetch VSJ Cheesecake with Biscoff sales for Jan 28 with promotion fix"""
    print("="*80)
    print("FETCHING CHEESECAKE WITH BISCOFF SALES - JANUARY 28")
    print("="*80)
    print()
    
    # Load credentials
    with open('clover_creds.json', 'r') as f:
        clover_creds_list = json.load(f)
    
    vsj_creds = None
    for cred in clover_creds_list:
        if cred['name'] == 'VSJ':
            vsj_creds = cred
            break
    
    if not vsj_creds:
        print("❌ ERROR: VSJ credentials not found")
        return 0
    
    merchant_id = vsj_creds['id']
    token = vsj_creds['token']
    category_id = vsj_creds['cookie_category_id']
    
    print(f"VSJ Merchant ID: {merchant_id}")
    print(f"Cookie Category ID: {category_id}")
    print()
    
    tz = ZoneInfo("America/Puerto_Rico")
    target_date = datetime(2026, 1, 28, 0, 0, 0, 0, tz)
    start_time = target_date
    end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tz)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    print(f"Date: {target_date.strftime('%B %d, %Y')}")
    print(f"Time Range: {start_ms} to {end_ms}")
    print()
    
    # Fetch orders
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
            print(f"❌ ERROR: API returned status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return 0
        
        orders = response.json().get('elements', [])
        print(f"✅ Found {len(orders)} total orders")
        
        # Filter by date
        filtered_orders = []
        for order in orders:
            order_time = order.get('createdTime', 0)
            if start_ms <= order_time <= end_ms:
                filtered_orders.append(order)
        
        print(f"✅ Orders on Jan 28: {len(filtered_orders)}")
        print()
        
        # Count Cheesecake with Biscoff
        print("[2] Counting Cheesecake with Biscoff sales...")
        count = 0
        items_found = []
        
        for order in filtered_orders:
            line_items = order.get('lineItems', {}).get('elements', [])
            for item in line_items:
                item_data = item.get('item', {})
                item_name = item_data.get('name', '')
                quantity = item.get('quantity', 0)
                refunded = item.get('refunded', False)
                is_revenue = item.get('isRevenue', True)
                
                # Check if it's Cheesecake with Biscoff
                if 'biscoff' in item_name.lower() and 'cheesecake' in item_name.lower():
                    # Check categories
                    categories = item_data.get('categories', {}).get('elements', [])
                    is_in_cookie_category = any(cat.get('id') == category_id for cat in categories)
                    
                    if not refunded and is_revenue and is_in_cookie_category:
                        items_found.append({
                            'name': item_name,
                            'quantity': quantity,
                            'order_id': order.get('id', '')
                        })
                        
                        # FIX: If quantity is 0 (promotion item), count as 1
                        if quantity == 0:
                            count += 1
                            print(f"  ✓ Promotion item: {item_name} (qty=0, counting as 1)")
                        else:
                            qty_decimal = quantity / 1000
                            count += int(qty_decimal)
                            print(f"  ✓ Normal item: {item_name} (qty={quantity}, counting as {int(qty_decimal)})")
        
        print()
        print(f"✅ Total Cheesecake with Biscoff sold: {count}")
        print(f"   Found {len(items_found)} line items")
        
        return count
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 0

def update_sheet(count):
    """Update Google Sheet with the count"""
    print()
    print("="*80)
    print("UPDATING GOOGLE SHEET")
    print("="*80)
    print()
    
    if count == 0:
        print("⚠️  Count is 0 - skipping update")
        return False
    
    # Load Google credentials
    print("[1] Loading Google Sheets credentials...")
    try:
        creds = Credentials.from_service_account_file(
            'service-account-key.json',
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=creds)
        print("✅ Credentials loaded")
    except Exception as e:
        print(f"❌ ERROR loading credentials: {e}")
        return False
    
    # Sheet ID and tab
    sheet_id = os.getenv('INVENTORY_SHEET_ID', '1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE')
    tab_name = "1-28"
    
    print(f"[2] Sheet ID: {sheet_id}")
    print(f"    Tab: {tab_name}")
    
    # Update cell BU16 (Old San Juan, Cheesecake with Biscoff, Live Sales Data)
    # Row 16 = Cheesecake with Biscoff
    # Column BU = Old San Juan "Live Sales Data"
    cell = "BU16"
    
    print(f"[3] Updating cell {cell} to {count}...")
    
    try:
        # First, read current value
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{tab_name}!{cell}"
        ).execute()
        
        current_value = result.get('values', [[0]])[0][0] if result.get('values') else 0
        print(f"    Current value: {current_value}")
        
        # Update to new value
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{tab_name}!{cell}",
            valueInputOption='RAW',
            body={'values': [[count]]}
        ).execute()
        
        print(f"✅ Successfully updated {cell} from {current_value} to {count}")
        return True
        
    except Exception as e:
        print(f"❌ ERROR updating sheet: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print()
    
    # Fetch count
    count = fetch_vsj_biscoff_jan28()
    
    if count > 0:
        print()
        print("="*80)
        response = input("Update Google Sheet? (yes/no): ").strip().lower()
        
        if response == 'yes':
            success = update_sheet(count)
            if success:
                print()
                print("="*80)
                print("✅ UPDATE COMPLETE!")
                print("="*80)
                print(f"Cheesecake with Biscoff for Jan 28 has been updated to {count}")
        else:
            print("\nUpdate cancelled")
    else:
        print("\n⚠️  No sales found - cannot update")
