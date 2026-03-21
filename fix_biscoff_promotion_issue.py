#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix for Cheesecake with Biscoff promotion items
This script can be run to manually update the sheet for Jan 28
and also provides the code fix needed
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

def clean_cookie_name(api_name):
    """Clean cookie name from API to match sheet format"""
    if not api_name:
        return ""
    
    cleaned = api_name.strip()
    
    # Handle *N* prefix
    if cleaned.startswith('*N*'):
        cleaned = cleaned.replace('*N*', '').strip()
    
    # Remove Clover prefixes like "*L*", "*C*", etc.
    if cleaned.startswith('*') and '*' in cleaned[1:]:
        second_star = cleaned.find('*', 1)
        if second_star != -1:
            cleaned = cleaned[second_star + 1:].strip()
    
    # Remove special Unicode characters
    special_chars = ['☆', '✩', '®', '™', '°', '∞', '∆', '∑', '∏', 'π', 'Ω']
    for char in special_chars:
        cleaned = cleaned.replace(char, '')
    
    # Map to sheet name
    if 'cheesecake' in cleaned.lower() and 'biscoff' in cleaned.lower():
        return "N - Cheesecake with Biscoff"
    
    return cleaned

def fetch_vsj_biscoff_jan28():
    """Fetch VSJ Cheesecake with Biscoff sales for Jan 28"""
    # Load credentials
    with open('clover_creds.json', 'r') as f:
        clover_creds_list = json.load(f)
    
    vsj_creds = None
    for cred in clover_creds_list:
        if cred['name'] == 'VSJ':
            vsj_creds = cred
            break
    
    if not vsj_creds:
        print("ERROR: VSJ credentials not found")
        return 0
    
    merchant_id = vsj_creds['id']
    token = vsj_creds['token']
    category_id = vsj_creds['cookie_category_id']
    
    tz = ZoneInfo("America/Puerto_Rico")
    target_date = datetime(2026, 1, 28, 0, 0, 0, 0, tz)
    start_time = target_date
    end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tz)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    # Fetch orders
    url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "filter": f"createdTime>={start_ms}",
        "expand": "lineItems,lineItems.item,lineItems.item.categories"
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    orders = response.json().get('elements', [])
    
    # Filter by date
    filtered_orders = []
    for order in orders:
        order_time = order.get('createdTime', 0)
        if start_ms <= order_time <= end_ms:
            filtered_orders.append(order)
    
    # Count Cheesecake with Biscoff
    count = 0
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
                    # FIX: If quantity is 0 (promotion item), count as 1
                    if quantity == 0:
                        count += 1
                    else:
                        count += int(quantity / 1000)
    
    return count

def update_sheet_manually():
    """Manually update the sheet for Jan 28"""
    count = fetch_vsj_biscoff_jan28()
    
    print(f"Found {count} Cheesecake with Biscoff sold on Jan 28")
    
    if count == 0:
        print("No sales found - cannot update")
        return
    
    # Load Google credentials
    creds = Credentials.from_service_account_file(
        'service-account-key.json',
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)
    
    # Sheet ID and tab
    sheet_id = os.getenv('INVENTORY_SHEET_ID', '1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE')
    tab_name = "1-28"
    
    # Update cell BU16 (Old San Juan, Cheesecake with Biscoff, Live Sales Data)
    # Column BU is index 72 (A=0, B=1, ..., BU=72)
    cell = "BU16"
    
    print(f"Updating {cell} to {count}...")
    
    try:
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{tab_name}!{cell}",
            valueInputOption='RAW',
            body={'values': [[count]]}
        ).execute()
        
        print(f"✅ Successfully updated {cell} to {count}")
    except Exception as e:
        print(f"❌ Error updating sheet: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("="*80)
    print("FIX FOR CHEESECAKE WITH BISCOFF - JANUARY 28")
    print("="*80)
    print()
    
    print("This script will:")
    print("1. Fetch actual sales count from Clover API (handling promotion items)")
    print("2. Update Google Sheet cell BU16 with the correct count")
    print()
    
    response = input("Do you want to update the sheet? (yes/no): ")
    if response.lower() == 'yes':
        update_sheet_manually()
    else:
        count = fetch_vsj_biscoff_jan28()
        print(f"\nFound {count} Cheesecake with Biscoff sold on Jan 28")
        print("Run with 'yes' to update the sheet")
