#!/usr/bin/env python3
"""
Check Clover API data for Cheesecake with Biscoff to see what's actually returned
"""

import os
import sys
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build

def load_clover_credentials():
    """Load Clover credentials"""
    try:
        with open('clover_creds.json', 'r') as f:
            creds_list = json.load(f)
        return creds_list
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None

def fetch_clover_orders(creds, target_date):
    """Fetch orders from Clover API for a specific date"""
    token = creds.get('token')
    merchant_id = creds.get('id')
    
    if not token or not merchant_id:
        print("Missing credentials")
        return []
    
    # Convert target_date to timestamp range
    tz = ZoneInfo("America/Puerto_Rico")
    start_datetime = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=tz)
    end_datetime = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=tz)
    
    start_timestamp = int(start_datetime.timestamp() * 1000)
    end_timestamp = int(end_datetime.timestamp() * 1000)
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
    params = {
        'filter': f'createdTime>={start_timestamp}&createdTime<={end_timestamp}',
        'expand': 'lineItems,lineItems.item,payments'
    }
    
    print(f"Fetching orders from Clover API...")
    print(f"  Date: {target_date}")
    print(f"  Timestamp range: {start_timestamp} to {end_timestamp}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get('elements', [])
    except Exception as e:
        print(f"Error fetching orders: {e}")
        return []

def analyze_biscoff_items(orders):
    """Analyze Cheesecake with Biscoff items"""
    print("\n" + "="*80)
    print("ANALYZING CHEESECAKE WITH BISCOFF ITEMS")
    print("="*80)
    
    biscoff_items = []
    total_count = 0
    
    for order in orders:
        line_items = order.get('lineItems', {}).get('elements', [])
        
        for line_item in line_items:
            item = line_item.get('item', {})
            item_name = item.get('name', '')
            quantity = line_item.get('unitQty', 0) / 1000.0  # Convert from milliunits
            
            # Check if refunded
            is_refunded = line_item.get('refunded', False)
            
            # Check if it's Cheesecake with Biscoff
            if 'biscoff' in item_name.lower() and 'cheesecake' in item_name.lower():
                biscoff_items.append({
                    'order_id': order.get('id'),
                    'item_name': item_name,
                    'quantity': quantity,
                    'is_refunded': is_refunded,
                    'created_time': order.get('createdTime'),
                    'item_id': item.get('id'),
                    'categories': [cat.get('name', '') for cat in item.get('categories', {}).get('elements', [])]
                })
                
                if not is_refunded:
                    total_count += quantity
    
    print(f"\nFound {len(biscoff_items)} Cheesecake with Biscoff line items")
    print(f"Total quantity (non-refunded): {int(total_count)}")
    
    if biscoff_items:
        print("\nItem Name Variations Found:")
        unique_names = {}
        for item in biscoff_items:
            name = item['item_name']
            if name not in unique_names:
                unique_names[name] = {
                    'count': 0,
                    'total_qty': 0,
                    'categories': item['categories']
                }
            unique_names[name]['count'] += 1
            if not item['is_refunded']:
                unique_names[name]['total_qty'] += item['quantity']
        
        for name, stats in unique_names.items():
            print(f"\n  Name: '{name}'")
            print(f"    Occurrences: {stats['count']}")
            print(f"    Total Quantity: {int(stats['total_qty'])}")
            print(f"    Categories: {', '.join(stats['categories']) if stats['categories'] else 'None'}")
            
            # Show the exact format
            print(f"    Raw bytes: {name.encode('utf-8')}")
            print(f"    Has *N* prefix: {'*N*' in name}")
            print(f"    Has *H* prefix: {'*H*' in name}")
            print(f"    Starts with *: {name.startswith('*')}")
    
    return biscoff_items, total_count

def main():
    """Main function"""
    print("="*80)
    print("CHECKING CLOVER DATA FOR CHEESECAKE WITH BISCOFF")
    print("="*80)
    
    # Load credentials
    creds_list = load_clover_credentials()
    if not creds_list:
        print("Failed to load credentials")
        return
    
    # Use today's date or yesterday
    tz = ZoneInfo("America/Puerto_Rico")
    today = datetime.now(tz).date()
    yesterday = today - timedelta(days=1)
    
    # Check VSJ (Old San Juan) specifically - that's where the issue is
    vsj_creds = None
    for cred in creds_list:
        if cred.get('name') == 'VSJ':
            vsj_creds = cred
            break
    
    if not vsj_creds:
        print("VSJ credentials not found")
        return
    
    print(f"Checking VSJ (Old San Juan) location")
    print(f"  Merchant ID: {vsj_creds.get('id')}")
    
    # Check both today and yesterday
    for check_date in [yesterday, today]:
        print(f"\n{'='*80}")
        print(f"Checking date: {check_date}")
        print(f"{'='*80}")
        
        orders = fetch_clover_orders(vsj_creds, check_date)
        print(f"Found {len(orders)} total orders")
        
        if orders:
            biscoff_items, total_count = analyze_biscoff_items(orders)
            
            if biscoff_items:
                print(f"\n✅ Found Cheesecake with Biscoff data for {check_date}")
                print(f"   Total sold: {int(total_count)}")
            else:
                print(f"\n⚠️  No Cheesecake with Biscoff items found for {check_date}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
