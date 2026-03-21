#!/usr/bin/env python3
"""
Quick backfill for Cheesecake with Biscoff - focuses on VSJ (Old San Juan)
Uses the NEW mapping logic with *N* support
"""

import os
import sys
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Disable ALL proxy settings
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)
os.environ['NO_PROXY'] = '*'

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

def clean_cookie_name(api_name):
    """Clean cookie name - NEW LOGIC with *N* mapping"""
    if not api_name:
        return ""
    
    cleaned = api_name.strip()
    
    # Check for *N* Cheesecake with Biscoff first
    if "*N* Cheesecake with Biscoff" in cleaned or "*N* Cheesecake with Biscoff®" in cleaned:
        return "N - Cheesecake with Biscoff"
    
    # Remove special chars
    for char in ['®', '™', '☆', 'Γå']:
        cleaned = cleaned.replace(char, '')
    
    # Remove *N* prefix if present
    if cleaned.startswith('*N*'):
        cleaned = cleaned.replace('*N*', '').strip()
    
    # Check if it's Cheesecake with Biscoff
    if 'cheesecake' in cleaned.lower() and 'biscoff' in cleaned.lower():
        return "N - Cheesecake with Biscoff"
    
    return cleaned

def fetch_vsj_biscoff(target_date):
    """Fetch VSJ Cheesecake with Biscoff sales"""
    with open('clover_creds.json', 'r') as f:
        creds_list = json.load(f)
    
    vsj_creds = None
    for cred in creds_list:
        if cred['name'] == 'VSJ':
            vsj_creds = cred
            break
    
    if not vsj_creds:
        print("VSJ credentials not found")
        return 0
    
    merchant_id = vsj_creds['id']
    token = vsj_creds['token']
    
    tz = ZoneInfo("America/Puerto_Rico")
    start_time = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, 0, tz)
    end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tz)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "filter": f"createdTime>={start_ms}",
        "expand": "lineItems,lineItems.item"
    }
    
    count = 0
    session = requests.Session()
    session.proxies = {}
    
    try:
        offset = 0
        limit = 100
        
        while True:
            params_with_limit = {**params, "limit": limit, "offset": offset}
            response = session.get(url, headers=headers, params=params_with_limit, timeout=30)
            
            if response.status_code != 200:
                break
            
            data = response.json()
            orders = data.get("elements", [])
            
            if not orders:
                break
            
            for order in orders:
                order_time = order.get('createdTime', 0)
                if order_time < start_ms or order_time > end_ms:
                    continue
                
                line_items = order.get('lineItems', {}).get('elements', [])
                for line_item in line_items:
                    if line_item.get('refunded', False):
                        continue
                    
                    item = line_item.get('item', {})
                    item_name = item.get('name', '')
                    
                    cleaned = clean_cookie_name(item_name)
                    if cleaned == "N - Cheesecake with Biscoff":
                        count += 1
            
            if len(orders) < limit:
                break
            
            offset += limit
        
        return count
        
    except Exception as e:
        print(f"Error: {e}")
        return 0

def update_sheet(tab_name, count):
    """Update Google Sheet"""
    creds = Credentials.from_service_account_file(
        "service-account-key.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    
    http = httplib2.Http(proxy_info=None)
    authorized_http = AuthorizedHttp(creds, http=http)
    service = build("sheets", "v4", http=authorized_http)
    sheet_id = "1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE"  # Correct sheet ID from URL
    
    # Read to find row 16 (Cheesecake with Biscoff) and column BU (Old San Juan)
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"'{tab_name}'!A16:BU16"
        ).execute()
        
        values = result.get('values', [])
        if not values or len(values) == 0:
            print(f"Could not read row 16 from tab '{tab_name}'")
            return False
        
        # Column BU is index 72 (A=0, B=1, ..., BU=72)
        # Update cell BU16
        cell_range = f"'{tab_name}'!BU16"
        
        body = {
            "valueInputOption": "RAW",
            "data": [{
                "range": cell_range,
                "values": [[str(count)]]
            }]
        }
        
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id,
            body=body
        ).execute()
        
        print(f"✅ Updated {cell_range} = {count}")
        return True
        
    except Exception as e:
        print(f"Error updating sheet: {e}")
        return False

def main():
    print("="*80)
    print("QUICK BACKFILL: Cheesecake with Biscoff - VSJ (Old San Juan)")
    print("="*80)
    
    # Use January 28 (the date mentioned in the issue)
    tz = ZoneInfo("America/Puerto_Rico")
    target_date = datetime(2026, 1, 28, 0, 0, 0, 0, tz)
    tab_name = "1-28"
    
    print(f"\nDate: {target_date.strftime('%B %d, %Y')}")
    print(f"Tab: {tab_name}")
    print(f"Location: VSJ (Old San Juan)")
    
    print(f"\n[1/2] Fetching Clover data...")
    count = fetch_vsj_biscoff(target_date)
    print(f"✅ Found: {count} Cheesecake with Biscoff sold")
    
    if count > 0:
        print(f"\n[2/2] Updating Google Sheet...")
        success = update_sheet(tab_name, count)
        if success:
            print(f"\n✅ SUCCESS! Updated Old San Juan to {count}")
        else:
            print(f"\n❌ Failed to update sheet")
    else:
        print(f"\n⚠️  No sales found - nothing to update")
    
    return count > 0

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
