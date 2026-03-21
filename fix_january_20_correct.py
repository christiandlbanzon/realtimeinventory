#!/usr/bin/env python3
"""
Use vm_inventory_updater functions to fetch correct API data and fix sheet
"""

import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Import from main script
import vm_inventory_updater

# Set target date
TARGET_DATE = datetime(2026, 1, 20, tzinfo=ZoneInfo("America/Puerto_Rico"))
os.environ['FOR_DATE'] = '2026-01-20'

def main():
    print("="*80)
    print("FETCHING CORRECT API DATA FOR JANUARY 20TH")
    print("="*80)
    
    # Load credentials
    clover_creds, shopify_creds = vm_inventory_updater.load_credentials()
    
    # Fetch sales data
    print("\n[1/2] Fetching sales data from APIs...")
    sales_data = vm_inventory_updater.fetch_sales_data(clover_creds, shopify_creds, TARGET_DATE)
    
    print("\n[2/2] Sales data summary:")
    for location, cookies in sales_data.items():
        print(f"\n{location}:")
        # Find Cookies & Cream and Chocolate Chip Nutella
        cookies_cream = 0
        chocolate_chip_nutella = 0
        
        for cookie_name, count in cookies.items():
            cleaned = vm_inventory_updater.clean_cookie_name(cookie_name)
            
            # Check for Cookies & Cream
            if 'cookies' in cleaned.lower() and 'cream' in cleaned.lower():
                cookies_cream += count
                print(f"  Cookies & Cream: '{cookie_name}' -> {count} (cleaned: '{cleaned}')")
            
            # Check for Chocolate Chip Nutella
            if 'chocolate' in cleaned.lower() and 'chip' in cleaned.lower() and 'nutella' in cleaned.lower():
                chocolate_chip_nutella += count
                print(f"  Chocolate Chip Nutella: '{cookie_name}' -> {count} (cleaned: '{cleaned}')")
        
        if cookies_cream > 0:
            print(f"  ✅ TOTAL Cookies & Cream: {cookies_cream}")
        if chocolate_chip_nutella > 0:
            print(f"  ✅ TOTAL Chocolate Chip Nutella: {chocolate_chip_nutella}")
    
    # Now update the sheet
    print("\n" + "="*80)
    print("UPDATING SHEET WITH CORRECT VALUES")
    print("="*80)
    
    # Set sheet ID to January sheet
    os.environ['INVENTORY_SHEET_ID'] = '1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE'
    
    # Update the sheet using the main function
    vm_inventory_updater.update_inventory_sheet(sales_data, TARGET_DATE)

if __name__ == "__main__":
    main()
