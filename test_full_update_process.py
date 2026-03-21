#!/usr/bin/env python3
"""
Test the full update process to see where the value becomes 1
"""

import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Get yesterday's date
tz = ZoneInfo("America/Puerto_Rico")
today = datetime.now(tz)
yesterday = today - timedelta(days=1)
TARGET_DATE = yesterday
TAB_NAME = f"{yesterday.month}-{yesterday.day}"

JANUARY_SHEET_ID = "1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

print("="*80)
print(f"TESTING FULL UPDATE PROCESS FOR PLAZA DEL SOL")
print(f"Date: {TARGET_DATE.strftime('%Y-%m-%d')} ({TAB_NAME})")
print("="*80)
print()

# Suppress logging
import logging
import io
sys.stderr = io.StringIO()
logging.disable(logging.CRITICAL)

# Import functions
from vm_inventory_updater import fetch_sales_data, update_inventory_sheet, find_cookie_row, clean_cookie_name

# Load credentials
with open("clover_creds.json", "r") as f:
    clover_creds_list = json.load(f)

clover_creds = {}
for cred in clover_creds_list:
    clover_creds[cred['name']] = cred

print("[1] Fetching sales data...")
sales_data = fetch_sales_data(clover_creds, {}, TARGET_DATE)

print(f"  Sales data keys: {list(sales_data.keys())}")
if 'PlazaSol' in sales_data:
    plaza_sales = sales_data['PlazaSol']
    print(f"  PlazaSol cookies: {len(plaza_sales)}")
    
    # Find Cookies & Cream
    for cookie_name, count in plaza_sales.items():
        if 'cookies' in cookie_name.lower() and 'cream' in cookie_name.lower():
            print(f"  Cookies & Cream: '{cookie_name}' = {count}")
else:
    print("  ERROR: PlazaSol not in sales_data!")

print()

print("[2] Reading sheet to get cookie names...")
service = build('sheets', 'v4', credentials=service_account.Credentials.from_service_account_file(
    'service-account-key.json', scopes=SCOPES))

range_name = f"{TAB_NAME}!A:CC"
result = service.spreadsheets().values().get(
    spreadsheetId=JANUARY_SHEET_ID, range=range_name
).execute()

values = result.get("values", [])
cookie_names = [row[0] for row in values[2:19] if row and row[0]]

print(f"  Found {len(cookie_names)} cookie names in sheet")
print(f"  First few: {cookie_names[:5]}")

# Check if 'C - Cookies & Cream' is in the list
if 'C - Cookies & Cream' in cookie_names:
    idx = cookie_names.index('C - Cookies & Cream')
    print(f"  'C - Cookies & Cream' found at index {idx} (row {idx + 3})")
else:
    print("  WARNING: 'C - Cookies & Cream' NOT FOUND in cookie_names!")
    print(f"  Looking for similar...")
    for i, name in enumerate(cookie_names):
        if 'cookies' in name.lower() and 'cream' in name.lower():
            print(f"    Found: '{name}' at index {i}")

print()

print("[3] Testing find_cookie_row...")
if 'PlazaSol' in sales_data:
    plaza_sales = sales_data['PlazaSol']
    for cookie_name, count in plaza_sales.items():
        if 'cookies' in cookie_name.lower() and 'cream' in cookie_name.lower():
            row = find_cookie_row(cookie_names, cookie_name)
            print(f"  '{cookie_name}' (count: {count}) -> row {row}")
            if row is None:
                print(f"    ERROR: Could not find row!")
            elif row != 5:
                print(f"    WARNING: Expected row 5, got row {row}")

print()

print("[4] Checking what would be written...")
if 'PlazaSol' in sales_data:
    plaza_sales = sales_data['PlazaSol']
    for cookie_name, count in plaza_sales.items():
        if 'cookies' in cookie_name.lower() and 'cream' in cookie_name.lower():
            row = find_cookie_row(cookie_names, cookie_name)
            if row:
                print(f"  Would write: '{cookie_name}' = {count} to row {row}")
                print(f"    This is correct!" if count == 14 else f"    ERROR: Expected 14, got {count}")

print()

print("[5] Checking location column mapping...")
location_row = values[0] if len(values) > 0 else []
headers = values[1] if len(values) > 1 else []

location_mapping = {
    "PlazaSol": "Plaza del Sol",
}

location_columns = {}
for i, header in enumerate(headers):
    if "Live Sales Data" in str(header) and "Do Not Touch" in str(header):
        location_name = ""
        if i < len(location_row) and location_row[i]:
            location_name = str(location_row[i]).strip()
        
        if "plaza del sol" in location_name.lower() or "plazasol" in location_name.lower():
            location_columns["Plaza del Sol"] = i
            print(f"  Found Plaza del Sol column: {chr(65 + i)} (index {i})")
            break

if "Plaza del Sol" not in location_columns:
    print("  ERROR: Could not find Plaza del Sol column!")

print()
print("="*80)
print("DIAGNOSIS")
print("="*80)
if 'PlazaSol' in sales_data:
    plaza_sales = sales_data['PlazaSol']
    cookies_cream_count = sum(count for name, count in plaza_sales.items() 
                              if 'cookies' in name.lower() and 'cream' in name.lower())
    print(f"Cookies & Cream count in sales_data: {cookies_cream_count}")
    print(f"Expected: 14")
    if cookies_cream_count != 14:
        print(f"  ERROR: Count mismatch!")
    else:
        print(f"  OK: Count is correct")
        
        # Check if row finding works
        for cookie_name, count in plaza_sales.items():
            if 'cookies' in cookie_name.lower() and 'cream' in cookie_name.lower():
                row = find_cookie_row(cookie_names, cookie_name)
                if row is None:
                    print(f"  ERROR: Could not find row for '{cookie_name}'")
                elif row != 5:
                    print(f"  WARNING: Row mismatch (expected 5, got {row})")
                else:
                    print(f"  OK: Row finding works correctly")
else:
    print("ERROR: PlazaSol not found in sales_data")

print("="*80)

# Restore stderr
sys.stderr = sys.__stderr__
