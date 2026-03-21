#!/usr/bin/env python3
"""
Test script to diagnose why Drunken Cookies sheet updates aren't working.
"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Set environment variable for a specific date
os.environ["FOR_DATE"] = "2026-01-17"
os.environ["PYTHONIOENCODING"] = "utf-8"

# Import and run the main script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main script functions
from vm_inventory_updater_fixed import (
    load_credentials,
    fetch_sales_data,
    update_drunken_cookies_sheet
)
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def main():
    print("=" * 80)
    print("TESTING DRUNKEN COOKIES SHEET UPDATE")
    print("=" * 80)
    
    target_date_str = os.getenv("FOR_DATE", "2026-01-17")
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    tz = ZoneInfo("America/Puerto_Rico")
    target_date_dt = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=tz)
    
    print(f"\nTarget Date: {target_date_str}")
    print(f"Target Date DT: {target_date_dt}")
    
    # Load credentials
    print("\n1. Loading credentials...")
    clover_creds, shopify_creds = load_credentials()
    print(f"   Clover locations: {list(clover_creds.keys())}")
    
    # Fetch sales data
    print("\n2. Fetching sales data...")
    sales_data = fetch_sales_data(clover_creds, shopify_creds, target_date)
    print(f"   Sales data locations: {list(sales_data.keys())}")
    
    for loc, cookies in sales_data.items():
        print(f"   {loc}: {len(cookies)} cookie types")
        if cookies:
            # Show first few items
            for cookie, count in list(cookies.items())[:5]:
                print(f"      - {cookie}: {count}")
    
    # Get service
    print("\n3. Getting Google Sheets service...")
    creds = Credentials.from_service_account_file(
        "service-account-key.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=creds)
    print("   Service created successfully")
    
    # Update Drunken Cookies sheet
    print("\n4. Updating Drunken Cookies sheet...")
    DRUNKEN_COOKIES_SHEET_ID = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"
    desired_tab = f"{target_date.month}-{target_date.day}"
    
    print(f"   Sheet ID: {DRUNKEN_COOKIES_SHEET_ID}")
    print(f"   Desired tab: {desired_tab}")
    print(f"   Sales data: {len(sales_data)} locations")
    
    try:
        update_drunken_cookies_sheet(
            service, DRUNKEN_COOKIES_SHEET_ID, sales_data, target_date_dt, desired_tab
        )
        print("\n✅ Update completed!")
    except Exception as e:
        print(f"\n❌ Error during update: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
