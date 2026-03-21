#!/usr/bin/env python3
"""Check which locations are in sales_data and if they map to Drunken Cookies tabs."""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vm_inventory_updater_fixed import load_credentials, fetch_sales_data

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "service-account-key.json")

from google.oauth2 import service_account
from googleapiclient.discovery import build

DRUNKEN_COOKIES_SHEET_ID = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"

def main():
    print("=" * 60)
    print("CHECKING DRUNKEN COOKIES LOCATION MAPPING")
    print("=" * 60)
    
    # Load credentials
    print("\n[1] Loading credentials...")
    clover_creds, shopify_creds = load_credentials()
    print(f"   Clover locations: {list(clover_creds.keys())}")
    print(f"   Shopify locations: {list(shopify_creds.keys())}")
    
    # Fetch sales data for a recent date
    print("\n[2] Fetching sales data for 2026-02-02...")
    tz = ZoneInfo("America/Puerto_Rico")
    target_date = datetime(2026, 2, 2, 0, 0, 0, tzinfo=tz)
    sales_data = fetch_sales_data(clover_creds, shopify_creds, target_date)
    print(f"   Sales data keys: {list(sales_data.keys())}")
    for loc, cookies in sales_data.items():
        print(f"   - {loc}: {len(cookies)} cookie types")
    
    # Check sheet tabs
    print("\n[3] Checking Drunken Cookies sheet tabs...")
    creds = service_account.Credentials.from_service_account_file(
        "service-account-key.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=creds)
    meta = service.spreadsheets().get(spreadsheetId=DRUNKEN_COOKIES_SHEET_ID).execute()
    tab_titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
    print(f"   Available tabs: {tab_titles}")
    
    # Check mapping
    print("\n[4] Checking location -> tab mapping...")
    LOC_TO_TAB = {
        "Plaza": "Plaza",
        "PlazaSol": "PlazaSol",
        "San Patricio": "San Patricio",
        "VSJ": "VSJ",
        "Montehiedra": "Montehiedra",
        "Plaza Carolina": "Plaza Carolina",
    }
    
    print("\n   Mapping results:")
    for loc in sales_data.keys():
        tab_name = LOC_TO_TAB.get(loc)
        if tab_name:
            if tab_name in tab_titles:
                print(f"   ✅ {loc} -> '{tab_name}' (tab exists)")
            else:
                print(f"   ⚠️  {loc} -> '{tab_name}' (tab NOT found)")
        else:
            print(f"   ❌ {loc} -> (no mapping)")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
