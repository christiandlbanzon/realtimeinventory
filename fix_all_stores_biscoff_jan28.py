#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Cheesecake with Biscoff for ALL stores on January 28
Checks all locations and updates their respective columns
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

# Location mapping: credential name -> sheet location name
LOCATION_MAPPING = {
    "Plaza": "Plaza Las Americas",
    "PlazaSol": "Plaza del Sol",
    "San Patricio": "San Patricio",
    "VSJ": "Old San Juan",
    "Montehiedra": "Montehiedra",
    "Plaza Carolina": "Plaza Carolina"
}

def fetch_biscoff_sales(creds, target_date):
    """Fetch Cheesecake with Biscoff sales for a location"""
    merchant_id = creds['id']
    token = creds['token']
    category_id = creds['cookie_category_id']
    
    tz = ZoneInfo("America/Puerto_Rico")
    start_time = target_date
    end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tz)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "filter": f"createdTime>={start_ms}",
        "expand": "lineItems,lineItems.item,lineItems.item.categories"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code != 200:
            return 0
        
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
                    categories = item_data.get('categories', {}).get('elements', [])
                    is_in_cookie_category = any(cat.get('id') == category_id for cat in categories)
                    
                    if not refunded and is_revenue and is_in_cookie_category:
                        # FIX: If quantity is 0 (promotion item), count as 1
                        if quantity == 0:
                            count += 1
                        else:
                            qty_decimal = quantity / 1000
                            count += int(qty_decimal)
        
        return count
    except Exception as e:
        print(f"  ERROR: {e}")
        return 0

def find_location_column(service, sheet_id, tab_name, location_name):
    """Find the column index for a location's Live Sales Data"""
    try:
        # Read headers and location row
        range_name = f"{tab_name}!A1:CC20"
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if len(values) < 2:
            return None
        
        location_row = values[0] if len(values) > 0 else []
        headers = values[1] if len(values) > 1 else []
        
        # Find column with "Live Sales Data" header and matching location
        for i, header in enumerate(headers):
            if "Live Sales Data" in str(header) and "Do Not Touch" in str(header):
                location_name_in_row = ""
                if i < len(location_row) and location_row[i]:
                    location_name_in_row = str(location_row[i]).strip()
                
                # Check if location matches
                if location_name.lower() in location_name_in_row.lower():
                    return i
        
        return None
    except Exception as e:
        print(f"  ERROR finding column: {e}")
        return None

def find_cookie_row(service, sheet_id, tab_name, cookie_name):
    """Find the row number for Cheesecake with Biscoff"""
    try:
        range_name = f"{tab_name}!A:A"
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        for i, row in enumerate(values):
            if row and len(row) > 0:
                if cookie_name.lower() in str(row[0]).lower():
                    return i + 1  # 1-indexed
        
        return None
    except Exception as e:
        print(f"  ERROR finding row: {e}")
        return None

def column_to_letter(n):
    """Convert column index to letter (0=A, 1=B, etc.)"""
    result = ""
    while n >= 0:
        result = chr(65 + (n % 26)) + result
        n = n // 26 - 1
    return result

def update_all_stores():
    """Update all stores' Biscoff data for Jan 28"""
    print("="*80)
    print("FIX CHEESECAKE WITH BISCOFF - ALL STORES - JANUARY 28")
    print("="*80)
    print()
    
    # Load credentials
    with open('clover_creds.json', 'r') as f:
        clover_creds_list = json.load(f)
    
    # Load Google credentials
    creds = Credentials.from_service_account_file(
        'service-account-key.json',
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)
    
    sheet_id = os.getenv('INVENTORY_SHEET_ID', '1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE')
    tab_name = "1-28"
    cookie_name = "N - Cheesecake with Biscoff"
    
    print(f"Sheet ID: {sheet_id}")
    print(f"Tab: {tab_name}")
    print(f"Cookie: {cookie_name}")
    print()
    
    # Find cookie row
    cookie_row = find_cookie_row(service, sheet_id, tab_name, cookie_name)
    if not cookie_row:
        print("❌ ERROR: Could not find cookie row")
        return
    
    print(f"Cookie row: {cookie_row}")
    print()
    
    # Process each location
    results = []
    
    for cred in clover_creds_list:
        location_cred_name = cred['name']
        location_sheet_name = LOCATION_MAPPING.get(location_cred_name, location_cred_name)
        
        print(f"[{location_sheet_name}]")
        print("-" * 60)
        
        # Fetch sales count
        target_date = datetime(2026, 1, 28, 0, 0, 0, 0, ZoneInfo("America/Puerto_Rico"))
        count = fetch_biscoff_sales(cred, target_date)
        
        print(f"  Sales count: {count}")
        
        if count == 0:
            print(f"  ⚠️  No sales found - skipping update")
            results.append({
                'location': location_sheet_name,
                'count': 0,
                'updated': False,
                'reason': 'No sales'
            })
            continue
        
        # Find column
        col_idx = find_location_column(service, sheet_id, tab_name, location_sheet_name)
        
        if col_idx is None:
            print(f"  ❌ Could not find column for {location_sheet_name}")
            results.append({
                'location': location_sheet_name,
                'count': count,
                'updated': False,
                'reason': 'Column not found'
            })
            continue
        
        col_letter = column_to_letter(col_idx)
        cell = f"{col_letter}{cookie_row}"
        
        print(f"  Column: {col_letter} (index {col_idx})")
        print(f"  Cell: {cell}")
        
        # Read current value
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=f"{tab_name}!{cell}"
            ).execute()
            
            current_value = result.get('values', [[0]])[0][0] if result.get('values') else 0
            print(f"  Current value: {current_value}")
            
            # Update
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=f"{tab_name}!{cell}",
                valueInputOption='RAW',
                body={'values': [[count]]}
            ).execute()
            
            print(f"  ✅ Updated from {current_value} to {count}")
            
            results.append({
                'location': location_sheet_name,
                'count': count,
                'updated': True,
                'cell': cell,
                'old_value': current_value
            })
            
        except Exception as e:
            print(f"  ❌ ERROR updating: {e}")
            results.append({
                'location': location_sheet_name,
                'count': count,
                'updated': False,
                'reason': str(e)
            })
        
        print()
    
    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print()
    
    updated = [r for r in results if r['updated']]
    failed = [r for r in results if not r['updated']]
    
    print(f"✅ Successfully updated: {len(updated)}")
    for r in updated:
        print(f"   {r['location']}: {r['old_value']} → {r['count']} (cell {r['cell']})")
    
    if failed:
        print(f"\n⚠️  Failed to update: {len(failed)}")
        for r in failed:
            print(f"   {r['location']}: {r['count']} sales found - {r.get('reason', 'Unknown error')}")
    
    print()

if __name__ == "__main__":
    update_all_stores()
