#!/usr/bin/env python3
"""
Fetch actual API data for January 20th and fix sheet values
"""

import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import requests

# Configuration
JANUARY_SHEET_ID = "1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE"
SERVICE_ACCOUNT_FILE = "service-account-key.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
TAB_NAME = "1-20"
TARGET_DATE = datetime(2026, 1, 20)

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def column_to_letter(column_index):
    """Convert a 0-indexed column number to a Google Sheet column letter."""
    result = ""
    while column_index >= 0:
        result = chr(65 + (column_index % 26)) + result
        column_index = column_index // 26 - 1
    return result

def get_sheet_service():
    """Authenticates and returns the Google Sheets service."""
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)

def get_sheet_info(service, sheet_id, tab_name):
    """Get sheet title, tab ID, location row, and headers."""
    sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheets = sheet_metadata.get('sheets', [])
    
    tab_id = None
    for sheet in sheets:
        if sheet['properties']['title'] == tab_name:
            tab_id = sheet['properties']['sheetId']
            break
    
    if tab_id is None:
        raise ValueError(f"Tab '{tab_name}' not found in sheet.")

    # Get headers and location row
    range_name = f"{tab_name}!A1:BZ2"
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=range_name
    ).execute()
    values = result.get('values', [])
    
    if len(values) < 2:
        raise ValueError("Not enough rows to get location and headers.")
    
    location_row = values[0]
    headers = values[1]
    
    return tab_id, location_row, headers

def get_cookie_row(service, sheet_id, tab_name, cookie_name_to_find):
    """Finds the row number for a given cookie name."""
    range_name = f"{tab_name}!A:A"
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=range_name
    ).execute()
    values = result.get('values', [])
    
    for i, row in enumerate(values):
        if row and row[0].strip() == cookie_name_to_find:
            return i + 1  # 1-indexed row number
    return None

def get_location_column(location_row, headers, target_location):
    """Finds the column index for a given location's 'Live Sales Data (Do Not Touch)' column."""
    for i, header in enumerate(headers):
        if "Live Sales Data" in str(header) and "Do Not Touch" in str(header):
            if i < len(location_row) and str(location_row[i]).strip() == target_location:
                return i  # 0-indexed column index
    return None

def fetch_clover_sales(creds, target_date):
    """Fetch Clover sales for a specific date."""
    merchant_id = creds.get('id')
    token = creds.get('token')
    cookie_category_id = creds.get('cookie_category_id')
    
    if not all([merchant_id, token, cookie_category_id]):
        return {}
    
    tz = ZoneInfo("America/Puerto_Rico")
    start_time = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, 0, tz)
    end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tz)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
    params = {
        "filter": f"createdTime>={start_ms}",
        "expand": "lineItems,lineItems.item,lineItems.item.categories"
    }
    
    all_orders = []
    offset = 0
    limit = 100
    
    while True:
        params_with_limit = {**params, "limit": limit, "offset": offset}
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params_with_limit,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"ERROR: API returned status {response.status_code}")
            break
        
        data = response.json()
        orders = data.get("elements", [])
        
        if not orders:
            break
        
        all_orders.extend(orders)
        
        if len(orders) < limit:
            break
        
        offset += limit
    
    # Filter orders by date
    filtered_orders = []
    for order in all_orders:
        created_time = order.get("createdTime", 0)
        if start_ms <= created_time <= end_ms:
            filtered_orders.append(order)
    
    # Count cookie sales
    cookie_sales = {}
    
    for order in filtered_orders:
        line_items = order.get("lineItems", {}).get("elements", [])
        
        for item in line_items:
            item_data = item.get("item", {})
            categories = item_data.get("categories", {}).get("elements", [])
            
            # Check if item belongs to cookie category
            is_cookie = False
            for cat in categories:
                if cat.get("id") == cookie_category_id:
                    is_cookie = True
                    break
            
            if is_cookie:
                cookie_name = item_data.get("name", "")
                # Each line item = 1 cookie sold (Clover API doesn't have quantity field)
                cookie_sales[cookie_name] = cookie_sales.get(cookie_name, 0) + 1
    
    return cookie_sales

def clean_cookie_name(api_name):
    """Clean cookie name for matching."""
    if not api_name:
        return ""
    
    cleaned = api_name.strip()
    
    # Remove Clover prefixes
    if cleaned.startswith('*') and '*' in cleaned[1:]:
        second_star = cleaned.find('*', 1)
        if second_star != -1:
            cleaned = cleaned[second_star + 1:].strip()
    
    # Remove special characters
    special_chars = ['®', '™', '°', '☆']
    for char in special_chars:
        cleaned = cleaned.replace(char, '')
    
    # Normalize "and" to "&"
    if ' and ' in cleaned.lower():
        cleaned = cleaned.replace(' and ', ' & ')
        cleaned = cleaned.replace(' And ', ' & ')
    
    return cleaned.strip()

def main():
    print("="*80)
    print("FETCHING API DATA FOR JANUARY 20TH AND FIXING SHEET VALUES")
    print("="*80)
    
    # Load credentials
    with open("clover_creds.json", "r") as f:
        clover_creds = json.load(f)
    
    # Get sheet service
    service = get_sheet_service()
    
    # Get sheet info
    tab_id, location_row, headers = get_sheet_info(service, JANUARY_SHEET_ID, TAB_NAME)
    
    # Fetch API data for each location
    print("\n[1/3] Fetching API data from Clover...")
    api_data = {}
    
    location_mapping = {
        "Plaza del Sol": "Plaza del Sol",
        "Plaza Carolina": "Plaza Carolina",
        "Plaza Las Americas": "Plaza Las Americas",
        "Old San Juan": "Old San Juan",
        "Montehiedra": "Montehiedra",
        "San Patricio": "San Patricio"
    }
    
    for sheet_location, api_location in location_mapping.items():
        if api_location in clover_creds:
            creds = clover_creds[api_location]
            print(f"  Fetching {api_location}...")
            sales = fetch_clover_sales(creds, TARGET_DATE)
            api_data[sheet_location] = sales
            print(f"    Found {len(sales)} cookie types")
            # Debug: Show all cookie names
            if sales:
                print(f"    Cookie names: {list(sales.keys())[:5]}...")
    
    # Find target cookies
    print("\n[2/3] Finding target cookies in sheet...")
    
    cookies_cream_row = get_cookie_row(service, JANUARY_SHEET_ID, TAB_NAME, "C - Cookies & Cream")
    chocolate_chip_nutella_row = get_cookie_row(service, JANUARY_SHEET_ID, TAB_NAME, "A - Chocolate Chip Nutella")
    
    if cookies_cream_row is None:
        print("ERROR: 'C - Cookies & Cream' row not found.")
        return
    if chocolate_chip_nutella_row is None:
        print("ERROR: 'A - Chocolate Chip Nutella' row not found.")
        return
    
    print(f"  Cookies & Cream at row {cookies_cream_row}")
    print(f"  Chocolate Chip Nutella at row {chocolate_chip_nutella_row}")
    
    # Find API values for these cookies
    print("\n[3/3] Comparing API data with sheet values...")
    
    target_updates = []
    
    # Check Cookies & Cream
    for location in location_mapping.keys():
        col_idx = get_location_column(location_row, headers, location)
        if col_idx is None:
            print(f"  Warning: Column not found for {location}")
            continue
        
        # Find Cookies & Cream in API data - check all variations
        cookies_cream_value = 0
        for api_name, count in api_data.get(location, {}).items():
            cleaned = clean_cookie_name(api_name)
            # Match variations: "Cookies & Cream", "Cookies and Cream", "*C* Cookies & Cream", etc.
            if ('cookies' in cleaned.lower() and 'cream' in cleaned.lower()) or \
               ('*c*' in api_name.lower() and 'cookies' in api_name.lower() and 'cream' in api_name.lower()):
                cookies_cream_value += count
                print(f"    Matched: '{api_name}' -> {count}")
        
        # Always add update if we have data (even if 0, to clear wrong values)
        target_updates.append({
            'row': cookies_cream_row,
            'col': col_idx,
            'value': cookies_cream_value,
            'cookie': 'Cookies & Cream',
            'location': location
        })
        print(f"  {location} - Cookies & Cream: {cookies_cream_value}")
    
    # Check Chocolate Chip Nutella
    for location in location_mapping.keys():
        col_idx = get_location_column(location_row, headers, location)
        if col_idx is None:
            continue
        
        # Find Chocolate Chip Nutella in API data - check all variations
        nutella_value = 0
        for api_name, count in api_data.get(location, {}).items():
            cleaned = clean_cookie_name(api_name)
            # Match variations: "Chocolate Chip Nutella", "*A* Chocolate Chip Nutella", etc.
            if ('chocolate' in cleaned.lower() and 'chip' in cleaned.lower() and 'nutella' in cleaned.lower()) or \
               ('*a*' in api_name.lower() and 'chocolate' in api_name.lower() and 'nutella' in api_name.lower()):
                nutella_value += count
                print(f"    Matched: '{api_name}' -> {count}")
        
        # Always add update if we have data (even if 0, to clear wrong values)
        target_updates.append({
            'row': chocolate_chip_nutella_row,
            'col': col_idx,
            'value': nutella_value,
            'cookie': 'Chocolate Chip Nutella',
            'location': location
        })
        print(f"  {location} - Chocolate Chip Nutella: {nutella_value}")
    
    # Update sheet
    print(f"\n[4/4] Updating sheet with {len(target_updates)} values...")
    
    if target_updates:
        requests = []
        for update in target_updates:
            requests.append({
                'updateCells': {
                    'range': {
                        'sheetId': tab_id,
                        'startRowIndex': update['row'] - 1,
                        'endRowIndex': update['row'],
                        'startColumnIndex': update['col'],
                        'endColumnIndex': update['col'] + 1
                    },
                    'rows': [{
                        'values': [{
                            'userEnteredValue': {'numberValue': float(update['value'])}
                        }]
                    }],
                    'fields': 'userEnteredValue'
                }
            })
            print(f"  Updating {update['location']} - {update['cookie']}: {update['value']}")
        
        body = {'requests': requests}
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=JANUARY_SHEET_ID,
            body=body
        ).execute()
        
        print(f"\n✅ Updated {len(requests)} cells successfully!")
    else:
        print("\n⚠️ No updates to make")

if __name__ == "__main__":
    main()
