#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive system check for real-time inventory updater
Checks:
1. Clover API credentials and connectivity
2. Google Sheets API access
3. Current sheet values
4. API data fetching capabilities
"""

import json
import os
import sys
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")

# ============================================================================
# 1. CHECK CREDENTIALS
# ============================================================================

def check_clover_credentials():
    """Check if Clover credentials file exists and is valid"""
    print_header("1. CHECKING CLOVER CREDENTIALS")
    
    creds_file = "clover_creds.json"
    
    if not os.path.exists(creds_file):
        print_error(f"Clover credentials file not found: {creds_file}")
        return None
    
    try:
        with open(creds_file, 'r') as f:
            creds_list = json.load(f)
        
        if not isinstance(creds_list, list):
            print_error("Credentials file is not a list")
            return None
        
        print_success(f"Found {len(creds_list)} Clover locations")
        
        creds_dict = {}
        for cred in creds_list:
            if not isinstance(cred, dict):
                print_warning(f"Skipping invalid credential entry: {cred}")
                continue
            
            name = cred.get('name', 'Unknown')
            merchant_id = cred.get('id', '')
            token = cred.get('token', '')
            category_id = cred.get('cookie_category_id', '')
            
            if not all([name, merchant_id, token, category_id]):
                print_warning(f"Incomplete credentials for {name}")
                continue
            
            creds_dict[name] = cred
            print_info(f"  {name}: Merchant ID {merchant_id[:8]}..., Token {token[:8]}..., Category {category_id[:8]}...")
        
        return creds_dict
        
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in credentials file: {e}")
        return None
    except Exception as e:
        print_error(f"Error reading credentials: {e}")
        return None

def check_google_credentials():
    """Check if Google service account credentials exist"""
    print_header("2. CHECKING GOOGLE SHEETS CREDENTIALS")
    
    creds_file = "service-account-key.json"
    
    if not os.path.exists(creds_file):
        print_error(f"Google service account file not found: {creds_file}")
        return None
    
    try:
        creds = Credentials.from_service_account_file(
            creds_file,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        print_success("Google service account credentials loaded")
        
        # Try to get project info
        with open(creds_file, 'r') as f:
            creds_data = json.load(f)
            project_id = creds_data.get('project_id', 'Unknown')
            client_email = creds_data.get('client_email', 'Unknown')
            print_info(f"  Project ID: {project_id}")
            print_info(f"  Client Email: {client_email}")
        
        return creds
        
    except Exception as e:
        print_error(f"Error loading Google credentials: {e}")
        return None

# ============================================================================
# 3. CHECK CLOVER API CONNECTIVITY
# ============================================================================

def test_clover_api(creds_dict):
    """Test Clover API connectivity for each location"""
    print_header("3. TESTING CLOVER API CONNECTIVITY")
    
    if not creds_dict:
        print_error("No credentials available to test")
        return {}
    
    results = {}
    
    for name, cred in creds_dict.items():
        merchant_id = cred['id']
        token = cred['token']
        
        print(f"\nTesting {name}...")
        print_info(f"  Merchant ID: {merchant_id}")
        
        try:
            # Test basic API connectivity
            url = f"https://api.clover.com/v3/merchants/{merchant_id}/items"
            headers = {"Authorization": f"Bearer {token}"}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                print_success(f"{name}: API connection successful")
                items = response.json().get('elements', [])
                print_info(f"  Found {len(items)} items")
                results[name] = True
            elif response.status_code == 401:
                print_error(f"{name}: Authentication failed (invalid token)")
                results[name] = False
            elif response.status_code == 404:
                print_error(f"{name}: Merchant not found (invalid merchant ID)")
                results[name] = False
            else:
                print_warning(f"{name}: Unexpected status code {response.status_code}")
                print_info(f"  Response: {response.text[:200]}")
                results[name] = False
                
        except requests.exceptions.Timeout:
            print_error(f"{name}: Connection timeout")
            results[name] = False
        except requests.exceptions.ConnectionError:
            print_error(f"{name}: Connection error (check internet)")
            results[name] = False
        except Exception as e:
            print_error(f"{name}: Error - {e}")
            results[name] = False
    
    return results

# ============================================================================
# 4. CHECK GOOGLE SHEETS ACCESS
# ============================================================================

def check_sheets_access(creds):
    """Check Google Sheets API access"""
    print_header("4. CHECKING GOOGLE SHEETS ACCESS")
    
    if not creds:
        print_error("No Google credentials available")
        return None
    
    try:
        service = build("sheets", "v4", credentials=creds)
        
        # Try to get sheet info (we'll use a known sheet ID from the codebase)
        # Check environment variable first
        sheet_id = os.getenv("INVENTORY_SHEET_ID")
        
        if not sheet_id:
            # Try common sheet IDs found in the codebase
            possible_sheet_ids = [
                "1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno",
                "1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE",
                "1zR0tPkqxMOijgQsmjLvg0cN2MlUuHlCB5VgNbNv3grU"
            ]
            
            print_warning("INVENTORY_SHEET_ID environment variable not set")
            print_info("Trying to detect sheet ID from codebase...")
            
            # Try each possible sheet ID
            for sid in possible_sheet_ids:
                try:
                    sheet_metadata = service.spreadsheets().get(spreadsheetId=sid).execute()
                    title = sheet_metadata.get('properties', {}).get('title', 'Unknown')
                    print_success(f"Found accessible sheet: {title} ({sid})")
                    sheet_id = sid
                    break
                except Exception as e:
                    continue
            
            if not sheet_id:
                print_error("Could not find accessible sheet. Please set INVENTORY_SHEET_ID environment variable")
                return None
        else:
            print_info(f"Using sheet ID from environment: {sheet_id}")
        
        # Test access
        try:
            sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            title = sheet_metadata.get('properties', {}).get('title', 'Unknown')
            print_success(f"Google Sheets API access successful")
            print_info(f"  Sheet Title: {title}")
            print_info(f"  Sheet ID: {sheet_id}")
            
            # List tabs
            sheets = sheet_metadata.get('sheets', [])
            tab_names = [s['properties']['title'] for s in sheets]
            print_info(f"  Found {len(tab_names)} tabs: {', '.join(tab_names[:10])}")
            if len(tab_names) > 10:
                print_info(f"  ... and {len(tab_names) - 10} more")
            
            return service, sheet_id
            
        except Exception as e:
            print_error(f"Cannot access sheet: {e}")
            return None
            
    except Exception as e:
        print_error(f"Error building Sheets service: {e}")
        return None

# ============================================================================
# 5. CHECK CURRENT SHEET VALUES
# ============================================================================

def check_current_sheet_values(service, sheet_id):
    """Check current values in the sheet"""
    print_header("5. CHECKING CURRENT SHEET VALUES")
    
    if not service or not sheet_id:
        print_error("No sheet access available")
        return
    
    try:
        # Get today's date
        tz = ZoneInfo("America/Puerto_Rico")
        today = datetime.now(tz)
        tab_name = f"{today.month}-{today.day}"
        
        print_info(f"Checking tab: {tab_name}")
        
        # Try to read a range
        try:
            range_name = f"{tab_name}!A1:Z20"
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                print_warning(f"Tab '{tab_name}' appears to be empty or doesn't exist")
                # Try yesterday's tab
                yesterday = today - timedelta(days=1)
                tab_name = f"{yesterday.month}-{yesterday.day}"
                print_info(f"Trying yesterday's tab: {tab_name}")
                
                range_name = f"{tab_name}!A1:Z20"
                result = service.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range=range_name
                ).execute()
                values = result.get('values', [])
            
            if values:
                print_success(f"Successfully read sheet data")
                print_info(f"  Found {len(values)} rows")
                
                # Show first few cookie names
                if len(values) > 2:
                    cookie_names = []
                    for i, row in enumerate(values[2:19], start=3):
                        if row and len(row) > 0:
                            cookie_names.append(f"Row {i}: {row[0]}")
                    
                    print_info(f"  Cookie names found:")
                    for name in cookie_names[:5]:
                        print(f"    {name}")
                    if len(cookie_names) > 5:
                        print(f"    ... and {len(cookie_names) - 5} more")
            else:
                print_warning("No data found in sheet")
                
        except Exception as e:
            print_error(f"Error reading sheet values: {e}")
            
    except Exception as e:
        print_error(f"Error checking sheet: {e}")

# ============================================================================
# 6. TEST FETCHING SALES DATA
# ============================================================================

def test_fetch_sales_data(creds_dict):
    """Test fetching sales data from Clover API"""
    print_header("6. TESTING SALES DATA FETCHING")
    
    if not creds_dict:
        print_error("No credentials available")
        return {}
    
    tz = ZoneInfo("America/Puerto_Rico")
    today = datetime.now(tz)
    yesterday = today - timedelta(days=1)
    
    # Test with yesterday's data (more likely to have sales)
    start_time = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0, 0, tz)
    end_time = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59, 999999, tz)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    print_info(f"Testing with date: {yesterday.strftime('%Y-%m-%d')}")
    print_info(f"  Time range: {start_ms} to {end_ms}")
    
    sales_results = {}
    
    for name, cred in creds_dict.items():
        merchant_id = cred['id']
        token = cred['token']
        category_id = cred['cookie_category_id']
        
        print(f"\nFetching sales for {name}...")
        
        try:
            url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
            headers = {"Authorization": f"Bearer {token}"}
            params = {
                "filter": f"createdTime>={start_ms}",
                "expand": "lineItems,lineItems.item,lineItems.item.categories"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                print_error(f"{name}: Failed to fetch orders (status {response.status_code})")
                sales_results[name] = {}
                continue
            
            orders = response.json().get("elements", [])
            
            # Filter orders by date
            filtered_orders = []
            for order in orders:
                created_time = order.get("createdTime", 0)
                if start_ms <= created_time <= end_ms:
                    filtered_orders.append(order)
            
            print_info(f"  Found {len(filtered_orders)} orders on {yesterday.strftime('%Y-%m-%d')}")
            
            # Count cookie sales
            cookie_sales = {}
            for order in filtered_orders:
                line_items = order.get("lineItems", {}).get("elements", [])
                for item in line_items:
                    item_data = item.get("item", {})
                    categories = item_data.get("categories", {}).get("elements", [])
                    
                    # Check if item belongs to cookie category
                    is_cookie = any(cat.get("id") == category_id for cat in categories)
                    
                    if is_cookie:
                        item_name = item_data.get("name", "Unknown")
                        cookie_sales[item_name] = cookie_sales.get(item_name, 0) + 1
            
            if cookie_sales:
                total = sum(cookie_sales.values())
                print_success(f"{name}: Found {total} cookie sales")
                print_info(f"  Cookie breakdown:")
                for cookie, count in sorted(cookie_sales.items())[:5]:
                    print(f"    {cookie}: {count}")
                if len(cookie_sales) > 5:
                    print(f"    ... and {len(cookie_sales) - 5} more cookie types")
            else:
                print_warning(f"{name}: No cookie sales found (orders exist but no cookies)")
            
            sales_results[name] = cookie_sales
            
        except Exception as e:
            print_error(f"{name}: Error fetching sales - {e}")
            sales_results[name] = {}
    
    return sales_results

# ============================================================================
# MAIN
# ============================================================================

def main():
    print_header("COMPREHENSIVE REAL-TIME INVENTORY SYSTEM CHECK")
    print_info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info("Checking LOCAL configuration and VM deployment...")
    
    # 1. Check credentials
    clover_creds = check_clover_credentials()
    google_creds = check_google_credentials()
    
    # 2. Test API connectivity
    api_results = {}
    if clover_creds:
        api_results = test_clover_api(clover_creds)
        
        # Summary
        successful = sum(1 for v in api_results.values() if v)
        total = len(api_results)
        print(f"\n{Colors.BOLD}API Connectivity Summary: {successful}/{total} locations working{Colors.END}")
    
    # 3. Check Sheets access
    sheets_result = check_sheets_access(google_creds)
    if sheets_result:
        service, sheet_id = sheets_result
        check_current_sheet_values(service, sheet_id)
    
    # 4. Test sales data fetching
    sales_data = {}
    if clover_creds:
        sales_data = test_fetch_sales_data(clover_creds)
        
        # Summary
        locations_with_sales = sum(1 for v in sales_data.values() if v)
        print(f"\n{Colors.BOLD}Sales Data Summary: {locations_with_sales}/{len(sales_data)} locations have sales data{Colors.END}")
    
    # 5. Check VM deployment (if gcloud is available)
    print_header("7. CHECKING VM DEPLOYMENT")
    try:
        import subprocess
        result = subprocess.run(['gcloud', '--version'], capture_output=True, timeout=5)
        if result.returncode == 0:
            print_info("gcloud CLI detected - checking VM deployment...")
            print_info("Run 'python check_vm_deployment.py' for detailed VM checks")
            print_warning("VM check skipped in this script - use check_vm_deployment.py for full VM verification")
        else:
            print_info("gcloud CLI not available - skipping VM checks")
    except:
        print_info("gcloud CLI not available - skipping VM checks")
    
    # Final summary
    print_header("CHECK COMPLETE")
    
    issues = []
    if not clover_creds:
        issues.append("Clover credentials missing or invalid")
    if not google_creds:
        issues.append("Google credentials missing or invalid")
    if clover_creds and api_results:
        failed_apis = [name for name, success in api_results.items() if not success]
        if failed_apis:
            issues.append(f"API connectivity issues: {', '.join(failed_apis)}")
    
    if issues:
        print_error("Issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print_success("All local checks passed! System appears to be configured correctly.")
        print_info("Next step: Run 'python check_vm_deployment.py' to verify VM deployment")
    
    print_info(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCheck interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
