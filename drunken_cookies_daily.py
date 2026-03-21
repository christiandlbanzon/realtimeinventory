#!/usr/bin/env python3
"""
Daily Drunken Cookies sheet updater
Updates ONLY the Drunken Cookies sheet (dates-as-rows layout)
Runs daily at 1 AM Puerto Rico to process yesterday's data
"""

import sys
import os

# Add current directory to path so we can import from vm_inventory_updater_fixed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vm_inventory_updater_fixed import (
    load_credentials,
    fetch_sales_data,
    update_drunken_cookies_sheet,
    get_target_date_for_processing
)
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

DRUNKEN_COOKIES_SHEET_ID = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"

def main():
    """Update ONLY Drunken Cookies sheet"""
    try:
        logging.info("🔄 Starting Drunken Cookies daily updater")
        
        # Get target date (ALWAYS yesterday for scheduled daily run at 1 AM PR)
        # This job runs at 1 AM Puerto Rico (5 AM UTC) to process yesterday's data
        tz = ZoneInfo("America/Puerto_Rico")
        # Explicitly get UTC time and convert to Puerto Rico timezone to avoid timezone issues
        utc_now = datetime.now(ZoneInfo("UTC"))
        pr_now = utc_now.astimezone(tz)
        
        # Always process yesterday's data for the scheduled daily run
        target_date_obj = (pr_now.date() - timedelta(days=1))
        target_date = datetime.combine(target_date_obj, datetime.min.time()).replace(tzinfo=tz)
        
        logging.info(f"📅 Target date: {target_date.strftime('%Y-%m-%d')} (yesterday for scheduled run)")
        logging.info(f"🕐 Current time: {pr_now.strftime('%Y-%m-%d %H:%M:%S %Z')} (UTC: {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')})")
        
        # Load credentials
        logging.info("🔑 Loading credentials...")
        clover_creds, shopify_creds = load_credentials()
        logging.info(f"✅ Credentials loaded: {len(clover_creds)} Clover locations")
        
        # Fetch sales data
        logging.info("📡 Fetching sales data...")
        sales_data = fetch_sales_data(clover_creds, shopify_creds, target_date)
        logging.info(f"✅ Sales data fetched: {len(sales_data)} locations")
        
        # Load Google Sheets service
        logging.info("🔑 Loading Google Sheets credentials...")
        creds = service_account.Credentials.from_service_account_file(
            "service-account-key.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        service = build("sheets", "v4", credentials=creds)
        
        # Update Drunken Cookies sheet ONLY
        logging.info("📝 Updating Drunken Cookies sheet...")
        desired_tab = f"{target_date.month}-{target_date.day}"
        update_drunken_cookies_sheet(
            service, DRUNKEN_COOKIES_SHEET_ID, sales_data, target_date, desired_tab
        )
        
        logging.info("✅ Drunken Cookies sheet updated successfully!")
        return True
        
    except Exception as e:
        logging.error(f"❌ Error: {e}")
        logging.error(f"Stack trace:", exc_info=True)
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            logging.info("🎉 Script completed successfully")
            sys.exit(0)
        else:
            logging.error("❌ Script completed with errors")
            sys.exit(1)
    except KeyboardInterrupt:
        logging.info("⏹️ Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"❌ Unhandled exception: {e}")
        logging.error(f"Stack trace:", exc_info=True)
        sys.exit(1)
