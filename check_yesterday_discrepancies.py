#!/usr/bin/env python3
"""
Diagnostic script to check discrepancies for Cookies & Cream
for Plaza Del Sol and OSJ (VSJ) for yesterday's date.
"""

import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuration
JANUARY_SHEET_ID = "1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Get yesterday's date (January 24, 2026)
tz = ZoneInfo("America/Puerto_Rico")
today = datetime.now(tz)
yesterday = today - timedelta(days=1)
TARGET_DATE = yesterday
TAB_NAME = f"{yesterday.month}-{yesterday.day}"  # e.g., "1-24"

print("="*80)
print(f"CHECKING DISCREPANCIES FOR {TARGET_DATE.strftime('%Y-%m-%d')} ({TAB_NAME})")
print("="*80)
print(f"Target locations: Plaza Del Sol, OSJ (VSJ)")
print(f"Target cookie: Cookies & Cream")
print()

def get_sheet_service():
    """Get Google Sheets service"""
    creds = service_account.Credentials.from_service_account_file(
        'service-account-key.json',
        scopes=SCOPES
    )
    return build('sheets', 'v4', credentials=creds)

def fetch_clover_sales(creds, target_date):
    """Fetch Clover sales for a specific date"""
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
        'access_token': token,
        'filter': f'createdTime>={start_ms}',
        'expand': 'lineItems',
        'limit': 1000
    }
    
    all_orders = []
    offset = 0
    limit = 100
    
    while True:
        params_with_limit = {**params, "limit": limit, "offset": offset}
        response = requests.get(url, params=params_with_limit, timeout=60)
        
        if response.status_code != 200:
            print(f"  ERROR: API returned status {response.status_code}")
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
            order_state = order.get('state', '')
            if order_state in ['locked', 'paid', 'open', 'completed']:
                filtered_orders.append(order)
    
    # Count cookie sales
    cookie_sales = {}
    
    for order in filtered_orders:
        line_items_data = order.get('lineItems', {})
        line_items = line_items_data.get('elements', [])
        
        for item in line_items:
            item_name = item.get('name', '')
            
            # Skip test items
            test_keywords = ['d:water', 'water', 'test', 'pick mini shots', 'shot glass', 'alcohol']
            if any(keyword in item_name.lower() for keyword in test_keywords):
                continue
            
            # Each line item = 1 unit sold
            quantity = 1
            
            # Clean cookie name
            cleaned_name = clean_cookie_name(item_name)
            
            if cleaned_name:
                cookie_sales[cleaned_name] = cookie_sales.get(cleaned_name, 0) + quantity
    
    return cookie_sales

def clean_cookie_name(api_name):
    """Clean cookie name from API to match sheet format"""
    if not api_name:
        return ""
    
    cleaned = api_name.strip()
    
    # Remove Clover prefixes like "*L*", "*C*", etc.
    if cleaned.startswith('*') and '*' in cleaned[1:]:
        second_star = cleaned.find('*', 1)
        if second_star != -1:
            cleaned = cleaned[second_star + 1:].strip()
    
    # Remove special Unicode characters
    special_chars = ['☆', 'Γå', '®', '™', '°', '∞', '∆', '∑', '∏', 'π', 'Ω']
    for char in special_chars:
        cleaned = cleaned.replace(char, '')
    
    # Normalize "and" to "&"
    if ' and ' in cleaned.lower():
        cleaned = cleaned.replace(' and ', ' & ')
        cleaned = cleaned.replace(' And ', ' & ')
    
    # Mapping for Cookies & Cream
    if 'cookies' in cleaned.lower() and 'cream' in cleaned.lower():
        return "C - Cookies & Cream"
    
    return cleaned

def get_sheet_values(service, sheet_id, tab_name, location_name):
    """Get sheet values for a specific location and cookie"""
    try:
        # First, get all sheet data to find location row and cookie row
        range_name = f"{tab_name}!A:ZZ"
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if not values:
            print(f"  ERROR: No data found in sheet tab {tab_name}")
            return None
        
        # Find location row (look for "Plaza Del Sol" or "OSJ" or "VSJ")
        location_row_idx = None
        location_col_idx = None
        
        for i, row in enumerate(values):
            for j, cell in enumerate(row):
                cell_str = str(cell).strip()
                if location_name.lower() in cell_str.lower():
                    location_row_idx = i
                    location_col_idx = j
                    break
            if location_row_idx is not None:
                break
        
        if location_row_idx is None:
            print(f"  ERROR: Location '{location_name}' not found in sheet")
            return None
        
        # Find cookie row (look for "Cookies & Cream" or "C - Cookies & Cream")
        cookie_row_idx = None
        cookie_name = None
        
        for i, row in enumerate(values):
            if i < 2:  # Skip header rows
                continue
            cookie_cell = row[0] if len(row) > 0 else ""
            cookie_str = str(cookie_cell).strip()
            
            if 'cookies' in cookie_str.lower() and 'cream' in cookie_str.lower():
                cookie_row_idx = i
                cookie_name = cookie_str
                break
        
        if cookie_row_idx is None:
            print(f"  ERROR: Cookies & Cream row not found in sheet")
            return None
        
        # Get the value at intersection of location column and cookie row
        # Need to find which column corresponds to the location
        # Location is typically in row 1 or 2, cookie is in column A
        
        # Find location column header
        header_row = values[1] if len(values) > 1 else []  # Usually row 2 (index 1)
        location_col_letter = None
        
        for j, header in enumerate(header_row):
            if location_name.lower() in str(header).lower():
                location_col_letter = chr(65 + j) if j < 26 else chr(64 + j // 26) + chr(65 + j % 26)
                location_col_idx = j
                break
        
        if location_col_idx is None:
            print(f"  ERROR: Could not find column for location '{location_name}'")
            return None
        
        # Get value at cookie row, location column
        cookie_row = values[cookie_row_idx] if cookie_row_idx < len(values) else []
        if location_col_idx < len(cookie_row):
            value_str = cookie_row[location_col_idx]
            try:
                value = float(value_str) if value_str else 0.0
            except (ValueError, TypeError):
                value = 0.0
        else:
            value = 0.0
        
        return {
            'cookie_name': cookie_name,
            'location': location_name,
            'value': value,
            'row': cookie_row_idx + 1,
            'col': location_col_idx + 1
        }
        
    except HttpError as error:
        print(f"  ERROR: {error}")
        return None

def main():
    # Load Clover credentials
    with open("clover_creds.json", "r") as f:
        clover_creds_list = json.load(f)
    
    # Convert to dict by name
    clover_creds = {}
    for cred in clover_creds_list:
        clover_creds[cred['name']] = cred
    
    # Get sheet service
    service = get_sheet_service()
    
    # Check each location
    locations_to_check = [
        ("Plaza Del Sol", "PlazaSol"),
        ("OSJ", "VSJ")  # OSJ might be labeled as VSJ or Old San Juan
    ]
    
    print(f"[1/2] Fetching Clover API data for {TARGET_DATE.strftime('%Y-%m-%d')}...")
    api_data = {}
    
    for sheet_location, api_location in locations_to_check:
        if api_location in clover_creds:
            print(f"  Fetching {api_location}...")
            creds = clover_creds[api_location]
            sales = fetch_clover_sales(creds, TARGET_DATE)
            api_data[sheet_location] = sales
            
            # Find Cookies & Cream value
            cookies_cream_value = 0
            for cookie_name, count in sales.items():
                if 'cookies' in cookie_name.lower() and 'cream' in cookie_name.lower():
                    cookies_cream_value += count
                    print(f"    Found: {cookie_name} = {count}")
            
            print(f"    Total Cookies & Cream: {cookies_cream_value}")
        else:
            print(f"  WARNING: {api_location} not found in credentials")
    
    print()
    print(f"[2/2] Reading sheet values from tab '{TAB_NAME}'...")
    sheet_data = {}
    
    # Try different location name variations
    location_variations = {
        "Plaza Del Sol": ["Plaza Del Sol", "Plaza del Sol", "PlazaDelSol"],
        "OSJ": ["OSJ", "VSJ", "Old San Juan", "Old San Juan (VSJ)"]
    }
    
    for sheet_location, variations in location_variations.items():
        found = False
        for variation in variations:
            result = get_sheet_values(service, JANUARY_SHEET_ID, TAB_NAME, variation)
            if result:
                sheet_data[sheet_location] = result
                print(f"  Found {variation}: Cookies & Cream = {result['value']} (row {result['row']}, col {result['col']})")
                found = True
                break
        
        if not found:
            print(f"  WARNING: Could not find location '{sheet_location}' in sheet")
    
    print()
    print("="*80)
    print("COMPARISON RESULTS")
    print("="*80)
    
    for sheet_location, api_location in locations_to_check:
        api_value = 0
        if sheet_location in api_data:
            for cookie_name, count in api_data[sheet_location].items():
                if 'cookies' in cookie_name.lower() and 'cream' in cookie_name.lower():
                    api_value += count
        
        sheet_value = 0
        if sheet_location in sheet_data:
            sheet_value = sheet_data[sheet_location]['value']
        
        print(f"\n{sheet_location}:")
        print(f"  Clover API: {api_value}")
        print(f"  Sheet:      {sheet_value}")
        
        if api_value != sheet_value:
            diff = api_value - sheet_value
            print(f"  DISCREPANCY: {diff:+.0f} (API {'higher' if diff > 0 else 'lower'})")
        else:
            print(f"  MATCH: Values are correct")

if __name__ == "__main__":
    main()
