#!/usr/bin/env python3
"""
Backfill Cheesecake with Biscoff data using the NEW mapping logic
This uses the fixed clean_cookie_name function with *N* mapping
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Disable ALL proxy settings completely
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy', 'NO_PROXY', 'no_proxy']:
    os.environ.pop(proxy_var, None)

# Also disable proxy in requests
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

def clean_cookie_name(api_name):
    """
    Clean cookie names from API to match sheet names - USING NEW LOGIC WITH *N* MAPPING
    This is the EXACT function from deploy_temp.sh with the Biscoff fix
    """
    if not api_name:
        return ""
    
    # Remove special characters and prefixes
    cleaned = api_name.strip()
    
    # SPECIAL HANDLING FOR MONTEHIEDRA: Check for exact matches first
    montehiedra_mapping = {
        "*A* Chocolate Chip Nutella ": "A - Chocolate Chip Nutella",
        "*B* Signature Chocolate Chip ": "B - Signature Chocolate Chip", 
        "*C* Cookies & Cream ": "C - Cookies & Cream",
        "*D* White Chocolate Macadamia ": "D - White Chocolate Macadamia",
        "*E* Churro with Dulce de Leche": "E - Churro with Dulce De Leche",
        "*F* Almond Chocolate ": "F - Almond Chocolate",
        "*G* Pecan Crme Brle": "G - Pecan Creme Brulee",
        "*H* Cheesecake with Biscoff": "H - Cheesecake with Biscoff",
        "*I* Tres Leches": "I - Tres Leches",
        "*J* Creepy Mummy Matcha": "J - Creepy Mummy Matcha",
        "*K* Strawberry Cheesecake": "K - Strawberry Cheesecake",
        "*L* S'mores": "L - S'mores",
        "*M* Dubai Chocolate": "M - Dubai Chocolate",
        "*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff",  # NEW FIX
        "*N* Cheesecake with Biscoff ": "N - Cheesecake with Biscoff",  # NEW FIX
    }
    
    # Check for exact Montehiedra match first
    for api_pattern, sheet_name in montehiedra_mapping.items():
        if api_pattern == cleaned:
            return sheet_name
    
    # Remove Clover prefixes like "*L*", "*C*", etc.
    if cleaned.startswith('*') and '*' in cleaned[1:]:
        # Find the second * and remove everything before it
        second_star = cleaned.find('*', 1)
        if second_star != -1:
            cleaned = cleaned[second_star + 1:].strip()
    
    # Remove special Unicode characters like ☆, Γå, ®, ™, etc.
    special_chars = ['☆', 'Γå', '®', '™', '°', '∞', '∆', '∑', '∏', 'π', 'Ω', 'α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ', 'ν', 'ξ', 'ο', 'ρ', 'σ', 'τ', 'υ', 'φ', 'χ', 'ψ', 'ω']
    for char in special_chars:
        cleaned = cleaned.replace(char, '')
    
    # Handle accented characters properly (don't remove them completely)
    accented_chars = {
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'á': 'a', 'à': 'a', 'â': 'a', 'ä': 'a', 'ã': 'a',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'ô': 'o', 'ö': 'o', 'õ': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n',
        'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
        'Á': 'A', 'À': 'A', 'Â': 'A', 'Ä': 'A', 'Ã': 'A',
        'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
        'Ó': 'O', 'Ò': 'O', 'Ô': 'O', 'Ö': 'O', 'Õ': 'O',
        'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
        'Ç': 'C', 'Ñ': 'N'
    }
    
    for accented, replacement in accented_chars.items():
        cleaned = cleaned.replace(accented, replacement)
    
    # Remove any remaining non-ASCII characters (except spaces)
    cleaned = ''.join(char if ord(char) < 128 or char.isspace() else '' for char in cleaned)
    
    # Remove extra whitespace
    cleaned = ' '.join(cleaned.split())
    
    # Normalize "and" to "&" for consistency
    if ' and ' in cleaned.lower():
        cleaned = cleaned.replace(' and ', ' & ')
        cleaned = cleaned.replace(' And ', ' & ')
    
    # Enhanced mapping for better matching
    name_mapping = {
        # Montehiedra-specific mappings
        "*A* Chocolate Chip Nutella": "A - Chocolate Chip Nutella",
        "*B* Signature Chocolate Chip": "B - Signature Chocolate Chip", 
        "*C* Cookies & Cream": "C - Cookies & Cream",
        "*C* Cookies and Cream": "C - Cookies & Cream",
        "*D* White Chocolate Macadamia": "D - White Chocolate Macadamia",
        "*E* Churro with Dulce de Leche": "E - Churro with Dulce De Leche",
        "*F* Almond Chocolate ": "F - Almond Chocolate",
        "*G* Pecan Crème Brûlée": "G - Pecan Creme Brulee",
        "*H* Cheesecake with Biscoff": "H - Cheesecake with Biscoff",
        "*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff",  # NEW FIX
        "*I* Tres Leches": "I - Tres Leches",
        "*J* Creepy Mummy Matcha": "J - Creepy Mummy Matcha",
        "*K* Strawberry Cheesecake": "K - Strawberry Cheesecake",
        "*L* S'mores": "L - S'mores",
        "*M* Dubai Chocolate": "M - Dubai Chocolate",
        
        # Montehiedra API names with trailing spaces
        "*A* Chocolate Chip Nutella ": "A - Chocolate Chip Nutella",
        "*B* Signature Chocolate Chip ": "B - Signature Chocolate Chip", 
        "*C* Cookies & Cream ": "C - Cookies & Cream",
        "*C* Cookies and Cream ": "C - Cookies & Cream",
        "*D* White Chocolate Macadamia ": "D - White Chocolate Macadamia",
        "*E* Churro with Dulce de Leche": "E - Churro with Dulce De Leche",
        "*F* Almond Chocolate ": "F - Almond Chocolate",
        "*G* Pecan Crme Brle": "G - Pecan Creme Brulee",
        "*H* Cheesecake with Biscoff": "H - Cheesecake with Biscoff",
        "*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff",  # NEW FIX
        "*N* Cheesecake with Biscoff ": "N - Cheesecake with Biscoff",  # NEW FIX
        "*I* Tres Leches": "I - Tres Leches",
        "*J* Creepy Mummy Matcha": "J - Creepy Mummy Matcha",
        "*K* Strawberry Cheesecake": "K - Strawberry Cheesecake",
        "*L* S'mores": "L - S'mores",
        "*M* Dubai Chocolate": "M - Dubai Chocolate",
        
        # Exact matches (fallback)
        "S'mores": "L - S'mores",
        "Cookies & Cream": "C - Cookies & Cream",
        "Cookies and Cream": "C - Cookies & Cream",
        "Chocolate Chip Nutella": "A - Chocolate Chip Nutella",
        "Signature Chocolate Chip": "B - Signature Chocolate Chip",
        "White Chocolate Macadamia": "D - White Chocolate Macadamia",
        "Churro with Dulce De Leche": "E - Churro with Dulce De Leche",
        "Almond Chocolate": "F - Almond Chocolate",
        "Cheesecake with Biscoff": "N - Cheesecake with Biscoff",  # NEW FIX - Changed from H to N
        "Lemon Poppyseed": "Lemon Poppyseed",
        "Tres Leches": "I - Tres Leches",
        "Creepy Mummy Matcha": "J - Creepy Mummy Matcha",
        "Strawberry Cheesecake": "K - Strawberry Cheesecake",
        "Midnight with Nutella": "Midnight with Nutella",
        "Midnight Nutella": "Midnight with Nutella",
        
        # Handle special characters and variations
        "Cookies & Cream Γå": "Cookies & Cream",
        "Chocolate Chip Nutella┬« Γå": "Chocolate Chip Nutella",
        "Cheesecake with Biscoff┬«": "N - Cheesecake with Biscoff",  # NEW FIX
        "*N* Cheesecake with Biscoff®": "N - Cheesecake with Biscoff",  # NEW FIX
        "*N* Cheesecake with Biscoff ": "N - Cheesecake with Biscoff",  # NEW FIX
        "Strawberry Cheesecake Γå": "Strawberry Cheesecake",
        "S'mores Γå": "S'mores",
        "Midnight with Nutella┬«": "Midnight with Nutella",
        "White Chocolate Macadamia Γå": "White Chocolate Macadamia"
    }
    
    # Try to find a match
    for api_pattern, sheet_name in name_mapping.items():
        if api_pattern.lower() in cleaned.lower():
            return sheet_name
    
    # Try to find a match with trailing spaces
    for api_pattern, sheet_name in name_mapping.items():
        if api_pattern.lower() in (cleaned + " ").lower():
            return sheet_name
    
    # If no exact mapping, try partial matching
    for api_pattern, sheet_name in name_mapping.items():
        pattern_words = set(api_pattern.lower().split())
        cleaned_words = set(cleaned.lower().split())
        
        common_words = {'the', 'with', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for'}
        pattern_words = pattern_words - common_words
        cleaned_words = cleaned_words - common_words
        
        if pattern_words and len(pattern_words.intersection(cleaned_words)) >= len(pattern_words) * 0.7:
            return sheet_name
    
    return cleaned

def column_to_letter(column_index):
    """Convert column index to letter (0=A, 1=B, etc.)"""
    result = ""
    while column_index >= 0:
        result = chr(65 + (column_index % 26)) + result
        column_index = column_index // 26 - 1
    return result

def find_cookie_row(cookie_names, api_cookie_name):
    """Find the row index for a cookie in the sheet"""
    cleaned_api_name = clean_cookie_name(api_cookie_name)
    
    # Debug: print what we're looking for
    print(f"    Looking for: '{cleaned_api_name}'")
    
    for i, sheet_cookie_name in enumerate(cookie_names, start=3):  # Start at row 3 (0-indexed)
        if not sheet_cookie_name:
            continue
        # Try exact match first
        if cleaned_api_name.lower() == sheet_cookie_name.lower().strip():
            print(f"    ✅ Found at row {i}: '{sheet_cookie_name}'")
            return i
        # Try partial match
        if 'biscoff' in cleaned_api_name.lower() and 'biscoff' in sheet_cookie_name.lower():
            if 'cheesecake' in cleaned_api_name.lower() and 'cheesecake' in sheet_cookie_name.lower():
                print(f"    ✅ Found at row {i} (partial match): '{sheet_cookie_name}'")
                return i
    
    # If not found, print available cookie names for debugging
    print(f"    Available cookie names:")
    for i, name in enumerate(cookie_names[:20], start=3):
        if name:
            print(f"      Row {i}: '{name}'")
    
    return None

def fetch_clover_sales(creds, target_date):
    """Fetch Clover sales for a specific location and date using NEW mapping logic"""
    merchant_id = creds['id']
    token = creds['token']
    cookie_category_id = creds.get('cookie_category_id')
    
    tz = ZoneInfo("America/Puerto_Rico")
    start_time = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, 0, tz)
    end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tz)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "filter": f"createdTime>={start_ms}",
        "expand": "lineItems,lineItems.item,lineItems.item.categories"
    }
    
    cookie_sales = {}
    
    # Create session without proxy
    session = requests.Session()
    session.proxies = {}
    
    try:
        offset = 0
        limit = 100
        
        while True:
            params_with_limit = {**params, "limit": limit, "offset": offset}
            response = session.get(url, headers=headers, params=params_with_limit, timeout=30)
            
            if response.status_code != 200:
                print(f"  ⚠️  API error: {response.status_code}")
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
                    item = line_item.get('item', {})
                    item_name = item.get('name', '')
                    
                    # Skip if refunded
                    if line_item.get('refunded', False):
                        continue
                    
                    # Count each line item as 1 unit (Clover API doesn't provide quantity field)
                    quantity = 1
                    
                    # Use NEW clean_cookie_name function
                    cleaned_name = clean_cookie_name(item_name)
                    
                    if cleaned_name:
                        if cleaned_name in cookie_sales:
                            cookie_sales[cleaned_name] += quantity
                        else:
                            cookie_sales[cleaned_name] = quantity
            
            if len(orders) < limit:
                break
            
            offset += limit
        
        return cookie_sales
        
    except Exception as e:
        print(f"  ❌ Error fetching sales: {e}")
        return {}

def backfill_biscoff_for_date(target_date, location_name=None):
    """Backfill Cheesecake with Biscoff for a specific date"""
    print("="*80)
    print(f"BACKFILLING CHEESECAKE WITH BISCOFF - {target_date.strftime('%Y-%m-%d')}")
    print("="*80)
    
    # Load Clover credentials
    with open('clover_creds.json', 'r') as f:
        creds_list = json.load(f)
    
    # Map credentials to sheet locations
    cred_to_sheet = {
        "Plaza": "Plaza Las Americas",
        "PlazaSol": "Plaza del Sol",
        "San Patricio": "San Patricio",
        "VSJ": "Old San Juan",
        "Montehiedra": "Montehiedra",
        "Plaza Carolina": "Plaza Carolina"
    }
    
    # Get sheet tab name - format is "1-28" for January 28
    tab_name = f"{target_date.month}-{target_date.day}"
    
    print(f"\n[1/5] Fetching sales data for {target_date.strftime('%B %d, %Y')}...")
    print(f"Tab name: {tab_name}")
    
    # Fetch sales for all locations or specific location
    all_sales = {}
    locations_to_process = [location_name] if location_name else list(cred_to_sheet.keys())
    
    for cred in creds_list:
        cred_name = cred["name"]
        if cred_name in locations_to_process:
            print(f"\n  Fetching {cred_name}...")
            sales = fetch_clover_sales(cred, target_date)
            sheet_location = cred_to_sheet[cred_name]
            all_sales[sheet_location] = sales
            
            # Check specifically for Biscoff
            biscoff_count = 0
            for cookie_name, count in sales.items():
                if 'biscoff' in cookie_name.lower() and 'cheesecake' in cookie_name.lower():
                    biscoff_count += count
                    print(f"    ✅ Found: {cookie_name} = {count}")
            
            if biscoff_count > 0:
                print(f"    📊 Total Cheesecake with Biscoff: {biscoff_count}")
            else:
                print(f"    ⚠️  No Cheesecake with Biscoff found")
    
    # Connect to Google Sheets
    print(f"\n[2/5] Connecting to Google Sheets...")
    creds = Credentials.from_service_account_file(
        "service-account-key.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    
    # Create HTTP without proxy
    http = httplib2.Http(proxy_info=None, disable_ssl_certificate_validation=False)
    authorized_http = AuthorizedHttp(creds, http=http)
    service = build("sheets", "v4", http=authorized_http)
    sheet_id = "1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno"
    
    print(f"Sheet ID: {sheet_id}")
    print(f"Tab: {tab_name}")
    
    # Read sheet structure
    print(f"\n[3/5] Reading sheet structure...")
    print(f"Tab name: {tab_name}")
    
    # First, list all sheets to find the correct tab name
    try:
        sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheet_titles = [sheet['properties']['title'] for sheet in sheet_metadata.get('sheets', [])]
        print(f"Available tabs ({len(sheet_titles)} total): {', '.join(sheet_titles[:20])}...")  # Show first 20
        
        # Look for January tabs specifically
        jan_tabs = [t for t in sheet_titles if t.startswith('1-')]
        if jan_tabs:
            print(f"January tabs found: {', '.join(jan_tabs)}")
            # Check if our target tab exists
            if tab_name not in sheet_titles:
                print(f"⚠️  Tab '{tab_name}' does not exist yet!")
                print(f"   Available January tabs: {', '.join(jan_tabs)}")
                print(f"   You may need to create the tab '{tab_name}' first")
                return False
        
        # Find matching tab - look for exact match first
        matching_tab = None
        month_str = str(target_date.month)
        day_str = str(target_date.day)
        exact_match = f"{month_str}-{day_str}"
        
        # First try exact match
        if exact_match in sheet_titles:
            matching_tab = exact_match
        else:
            # Try with leading zero
            exact_match_zero = f"{target_date.month:02d}-{target_date.day:02d}"
            if exact_match_zero in sheet_titles:
                matching_tab = exact_match_zero
            else:
                # Fallback: look for tab containing month and day
                for title in sheet_titles:
                    # Check if tab matches date pattern exactly
                    if title == exact_match or title == exact_match_zero:
                        matching_tab = title
                        break
                    # Or contains both month and day
                    if month_str in title and day_str in title:
                        # Make sure it's not matching wrong month (e.g., "11-28" when looking for "1-28")
                        parts = title.split('-')
                        if len(parts) == 2:
                            try:
                                tab_month = int(parts[0])
                                tab_day = int(parts[1])
                                if tab_month == target_date.month and tab_day == target_date.day:
                                    matching_tab = title
                                    break
                            except:
                                pass
        
        if matching_tab:
            tab_name = matching_tab
            print(f"✅ Found matching tab: '{tab_name}'")
        else:
            print(f"⚠️  No exact match found, trying: '{tab_name}'")
    except Exception as e:
        print(f"⚠️  Could not list sheets: {e}")
        print(f"Using default tab name: '{tab_name}'")
    
    try:
        # Try with quotes first (for tabs with special characters)
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=f"'{tab_name}'!A:BX"
            ).execute()
        except:
            # If that fails, try without quotes
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=f"{tab_name}!A:BX"
            ).execute()
        
        values = result.get("values", [])
        if len(values) < 3:
            print(f"❌ ERROR: Tab '{tab_name}' not found or insufficient data")
            return False
        
        location_row = values[0] if len(values) > 0 else []
        headers = values[1] if len(values) > 1 else []
        cookie_rows = values[2:20] if len(values) > 2 else []
        cookie_names = [row[0] if row and len(row) > 0 else "" for row in cookie_rows]
        
        print(f"Found {len(cookie_names)} cookie rows")
        
        # Find Live Sales Data columns
        print(f"\n[4/5] Finding Live Sales Data columns...")
        location_columns = {}
        
        for i, header in enumerate(headers):
            header_str = str(header).lower() if header else ""
            location_str = str(location_row[i]).lower() if i < len(location_row) and location_row[i] else ""
            
            if "live sales data" in header_str and "do not touch" in header_str:
                # Match to known locations
                for sheet_location in cred_to_sheet.values():
                    if sheet_location.lower() in location_str or location_str in sheet_location.lower():
                        if sheet_location not in location_columns:
                            location_columns[sheet_location] = i
                            print(f"  ✅ {sheet_location}: Column {column_to_letter(i)}")
                            break
        
        # Prepare updates
        print(f"\n[5/5] Preparing updates...")
        updates = []
        
        for sheet_location, sales_data in all_sales.items():
            if sheet_location not in location_columns:
                print(f"  ⚠️  Skipping {sheet_location} - column not found")
                continue
            
            col_idx = location_columns[sheet_location]
            
            # Focus on Cheesecake with Biscoff
            biscoff_name = "N - Cheesecake with Biscoff"
            biscoff_count = sales_data.get(biscoff_name, 0)
            
            if biscoff_count > 0:
                row_num = find_cookie_row(cookie_names, "*N* Cheesecake with Biscoff")
                
                if row_num:
                    cell_range = f"{tab_name}!{column_to_letter(col_idx)}{row_num}"
                    updates.append({
                        "range": cell_range,
                        "values": [[str(biscoff_count)]]
                    })
                    print(f"  ✅ {sheet_location}: {biscoff_name} = {biscoff_count} -> {cell_range}")
                else:
                    print(f"  ⚠️  Could not find row for {biscoff_name}")
        
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
        print("✅ SUCCESS: Cheesecake with Biscoff backfilled!")
        print(f"Updated {len(updates)} locations")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    print("="*80)
    print("BACKFILL CHEESECAKE WITH BISCOFF - USING NEW MAPPING LOGIC")
    print("="*80)
    
    # Test the mapping first
    print("\n[TEST] Verifying new mapping logic...")
    test_cases = [
        ("*N* Cheesecake with Biscoff®", "N - Cheesecake with Biscoff"),
        ("*N* Cheesecake with Biscoff", "N - Cheesecake with Biscoff"),
        ("*N* Cheesecake with Biscoff ", "N - Cheesecake with Biscoff"),
    ]
    
    all_passed = True
    for api_name, expected in test_cases:
        result = clean_cookie_name(api_name)
        if result == expected:
            print(f"  ✅ '{api_name}' -> '{result}'")
        else:
            print(f"  ❌ '{api_name}' -> '{result}' (expected '{expected}')")
            all_passed = False
    
    if not all_passed:
        print("\n❌ Mapping tests failed! Fix the clean_cookie_name function first.")
        return False
    
    print("\n✅ All mapping tests passed!")
    
    # Backfill for January dates
    tz = ZoneInfo("America/Puerto_Rico")
    
    # Try January 28 first (the date mentioned in the issue)
    target_date = datetime(2026, 1, 28, 0, 0, 0, 0, tz)
    
    print(f"\n{'='*80}")
    print(f"BACKFILLING {target_date.strftime('%B %d, %Y').upper()}")
    print(f"{'='*80}")
    
    # Backfill all locations
    success = backfill_biscoff_for_date(target_date)
    
    # If Jan 28 tab doesn't exist, try the latest available January tab
    if not success:
        print(f"\n{'='*80}")
        print("Trying latest available January tab...")
        print(f"{'='*80}")
        
        # Get available tabs
        creds = Credentials.from_service_account_file(
            "service-account-key.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        http = httplib2.Http(proxy_info=None)
        authorized_http = AuthorizedHttp(creds, http=http)
        service = build("sheets", "v4", http=authorized_http)
        
        sheet_metadata = service.spreadsheets().get(spreadsheetId="1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno").execute()
        sheet_titles = [sheet['properties']['title'] for sheet in sheet_metadata.get('sheets', [])]
        jan_tabs = sorted([t for t in sheet_titles if t.startswith('1-')])
        
        if jan_tabs:
            latest_jan = jan_tabs[-1]
            print(f"Using latest available tab: '{latest_jan}'")
            parts = latest_jan.split('-')
            if len(parts) == 2:
                try:
                    target_date = datetime(2026, int(parts[0]), int(parts[1]), 0, 0, 0, 0, tz)
                    success = backfill_biscoff_for_date(target_date)
                except Exception as e:
                    print(f"Error: {e}")
    
    # Also try yesterday and today
    today = datetime.now(tz).date()
    yesterday = today - timedelta(days=1)
    
    if target_date.date() != yesterday:
        print(f"\n{'='*80}")
        print(f"BACKFILLING {yesterday.strftime('%B %d, %Y')}")
        print(f"{'='*80}")
        backfill_biscoff_for_date(datetime.combine(yesterday, datetime.min.time()).replace(tzinfo=tz))
    
    if target_date.date() != today:
        print(f"\n{'='*80}")
        print(f"BACKFILLING {today.strftime('%B %d, %Y')}")
        print(f"{'='*80}")
        backfill_biscoff_for_date(datetime.combine(today, datetime.min.time()).replace(tzinfo=tz))
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
