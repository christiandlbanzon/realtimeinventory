#!/usr/bin/env python3
"""
Backfill Cheesecake with Biscoff for ALL stores on January 28
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

def column_to_letter(column_index):
    """Convert column index to letter (0=A, 1=B, etc.)"""
    result = ""
    while column_index >= 0:
        result = chr(65 + (column_index % 26)) + result
        column_index = column_index // 26 - 1
    return result

def fetch_clover_sales(creds, target_date):
    """Fetch Clover sales for a location"""
    merchant_id = creds['id']
    token = creds['token']
    
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
        print(f"  Error: {e}")
        return 0

def main():
    print("="*80)
    print("BACKFILL ALL STORES - CHEESECAKE WITH BISCOFF - JANUARY 28")
    print("="*80)
    
    # Load Clover credentials
    with open('clover_creds.json', 'r') as f:
        creds_list = json.load(f)
    
    # Map credentials to sheet locations and columns
    cred_to_sheet = {
        "Plaza": ("Plaza Las Americas", "BJ"),  # Column BJ
        "PlazaSol": ("Plaza del Sol", "T"),     # Column T
        "San Patricio": ("San Patricio", "G"),  # Column G
        "VSJ": ("Old San Juan", "BU"),          # Column BU
        "Montehiedra": ("Montehiedra", "AG"),   # Column AG
        "Plaza Carolina": ("Plaza Carolina", "AT")  # Column AT
    }
    
    tz = ZoneInfo("America/Puerto_Rico")
    target_date = datetime(2026, 1, 28, 0, 0, 0, 0, tz)
    tab_name = "1-28"
    row_num = 16  # Row 16 = N - Cheesecake with Biscoff
    
    print(f"\nDate: {target_date.strftime('%B %d, %Y')}")
    print(f"Tab: {tab_name}")
    print(f"Row: {row_num} (N - Cheesecake with Biscoff)")
    
    # Fetch sales for all locations
    print(f"\n[1/3] Fetching Clover data for all stores...")
    sales_data = {}
    
    for cred in creds_list:
        cred_name = cred["name"]
        if cred_name in cred_to_sheet:
            print(f"\n  Fetching {cred_name}...")
            count = fetch_clover_sales(cred, target_date)
            sales_data[cred_name] = count
            sheet_location, column = cred_to_sheet[cred_name]
            print(f"    ✅ {sheet_location}: {count} sold")
    
    # Connect to Google Sheets
    print(f"\n[2/3] Connecting to Google Sheets...")
    creds = Credentials.from_service_account_file(
        "service-account-key.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    
    http = httplib2.Http(proxy_info=None)
    authorized_http = AuthorizedHttp(creds, http=http)
    service = build("sheets", "v4", http=authorized_http)
    sheet_id = "1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE"  # Correct sheet ID
    
    # Prepare updates
    print(f"\n[3/3] Preparing updates...")
    updates = []
    
    for cred_name, count in sales_data.items():
        if cred_name in cred_to_sheet:
            sheet_location, column_letter = cred_to_sheet[cred_name]
            cell_range = f"'{tab_name}'!{column_letter}{row_num}"
            
            updates.append({
                "range": cell_range,
                "values": [[str(count)]]
            })
            
            print(f"  ✅ {sheet_location} ({column_letter}{row_num}): {count}")
    
    if not updates:
        print("  ⚠️  No updates to make")
        return False
    
    # Write to sheet
    print(f"\nWriting {len(updates)} updates to sheet...")
    body = {
        "valueInputOption": "RAW",
        "data": updates
    }
    
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id,
        body=body
    ).execute()
    
    print("\n" + "="*80)
    print("✅ SUCCESS! All stores updated!")
    print("="*80)
    print(f"\nUpdated {len(updates)} stores:")
    for cred_name, count in sales_data.items():
        if cred_name in cred_to_sheet:
            sheet_location, _ = cred_to_sheet[cred_name]
            print(f"  • {sheet_location}: {count}")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
