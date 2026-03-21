#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script to check Brookie data for Feb 7, 2026"""

import json
import os
import sys
import codecs
from datetime import datetime
from zoneinfo import ZoneInfo

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vm_inventory_updater_fixed import fetch_clover_sales, clean_cookie_name, load_credentials

def main():
    print("=" * 60)
    print("TESTING BROOKIE DATA FOR FEB 7, 2026")
    print("=" * 60)
    
    # Load credentials
    creds_list = load_credentials()
    
    # Find Montehiedra credentials
    montehiedra_creds = None
    for cred in creds_list:
        if cred.get('name') == 'Montehiedra':
            montehiedra_creds = cred
            break
    
    if not montehiedra_creds:
        print("[ERROR] Montehiedra credentials not found!")
        return
    
    print(f"\n[OK] Found Montehiedra credentials")
    print(f"   Merchant ID: {montehiedra_creds.get('id')}")
    
    # Set target date to Feb 7, 2026
    tz = ZoneInfo("America/Puerto_Rico")
    target_date = datetime(2026, 2, 7, 0, 0, 0, 0, tz)
    
    print(f"\n📅 Fetching sales data for: {target_date.strftime('%Y-%m-%d')}")
    
    # Fetch sales data
    sales_data = fetch_clover_sales(montehiedra_creds, target_date)
    
    print(f"\n📊 Raw sales data from Clover:")
    print(f"   Total cookie types: {len(sales_data)}")
    
    # Check for Brookie-related entries
    brookie_entries = {}
    f_entries = {}
    
    for cookie_name, count in sales_data.items():
        cookie_lower = cookie_name.lower()
        if 'brookie' in cookie_lower:
            brookie_entries[cookie_name] = count
        if cookie_name.startswith('*F*'):
            f_entries[cookie_name] = count
    
    print(f"\n[SEARCH] Brookie-related entries:")
    if brookie_entries:
        for name, count in brookie_entries.items():
            cleaned = clean_cookie_name(name)
            print(f"   '{name}' -> '{cleaned}': {count}")
    else:
        print("   [ERROR] No Brookie entries found!")
    
    print(f"\n[SEARCH] All *F* entries:")
    if f_entries:
        for name, count in f_entries.items():
            cleaned = clean_cookie_name(name)
            print(f"   '{name}' -> '{cleaned}': {count}")
    else:
        print("   [ERROR] No *F* entries found!")
    
    # Check what clean_cookie_name returns for "*F* Brookie"
    print(f"\n[TEST] Testing clean_cookie_name:")
    test_names = [
        "*F* Brookie",
        "*F* Brookie ",
        "*F* Almond Chocolate",
        "*F* Almond Chocolate ",
    ]
    
    for test_name in test_names:
        cleaned = clean_cookie_name(test_name)
        print(f"   '{test_name}' -> '{cleaned}'")
    
    # Check consolidated sales
    print(f"\n📊 Consolidated sales data:")
    total_brookie = 0
    for cookie_name, count in sales_data.items():
        cleaned = clean_cookie_name(cookie_name)
        if cleaned == "F - Brookie":
            total_brookie += count
            print(f"   '{cookie_name}' -> '{cleaned}': {count}")
    
    print(f"\n[RESULT] Total Brookie sales (consolidated): {total_brookie}")
    print(f"   Expected: 10")
    
    if total_brookie == 10:
        print("   [OK] CORRECT!")
    else:
        print(f"   [ERROR] MISMATCH! Expected 10, got {total_brookie}")

if __name__ == "__main__":
    main()
