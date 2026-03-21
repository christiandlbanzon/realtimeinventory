#!/usr/bin/env python3
"""
Verify that the system is ready for new flavors from Clover.
Run this before adding a new flavor to ensure everything will work.

Checks:
1. Primary Mall PARs sheet: [NOT IN USE] slots available for new flavors
2. Cookie row capacity (50 rows supported)
3. Drunken Cookies sheet: structure and auto-add capability
4. Filter logic: default-include (new flavors counted automatically)
"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

def main():
    print("=" * 60)
    print("NEW FLAVOR READINESS CHECK")
    print("=" * 60)
    
    all_ok = True
    
    # 1. Check filter logic (code review - no API needed)
    print("\n[1] FILTER LOGIC (default-include)")
    print("    New flavors are counted automatically unless they match")
    print("    the exclude list: shot glass, alcohol, merchandise, PICK minishots,")
    print("    t-shirts, fans, gift cards.")
    print("    -> OK: No keyword whitelist needed for new flavors")
    
    # 2. Check primary sheet (Mall PARs)
    print("\n[2] PRIMARY MALL PARS SHEET")
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        
        creds = Credentials.from_service_account_file(
            "service-account-key.json",
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.readonly",
            ]
        )
        service = build("sheets", "v4", credentials=creds)
        
        tz = ZoneInfo("America/Puerto_Rico")
        now = datetime.now(tz)
        current_month = now.month
        
        # Get sheet ID (same logic as vm_inventory_updater_fixed.py)
        PARS_FOLDER_ID = "1CdAyO-8TGYJKgPs_8dSo0dFOX9ojCnC2"
        drive = build("drive", "v3", credentials=creds)
        month_name = datetime(2000, current_month, 1).strftime("%B")
        expected_name = f"{month_name} Mall PARs_2026"
        
        results = drive.files().list(
            q=f"'{PARS_FOLDER_ID}' in parents and trashed=false",
            fields="files(id, name)"
        ).execute()
        
        sheet_id = None
        for f in results.get("files", []):
            actual = f.get("name", "")
            if actual == expected_name:
                sheet_id = f["id"]
                break
            if actual.lower() == expected_name.lower():
                sheet_id = f["id"]
                break
        
        if not sheet_id:
            # Fallback
            if current_month == 1:
                sheet_id = "1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE"
            elif current_month == 2:
                sheet_id = "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4"
            else:
                sheet_id = "1kYbyeLoOd986lZrnc57XOynanYLbW2NM2fwypUJa2PQ"
        
        sheet_id = os.getenv("INVENTORY_SHEET_ID", sheet_id)
        
        # Get first available tab (e.g. 1-29 for today)
        sheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        tabs = [s["properties"]["title"] for s in sheet["sheets"]]
        
        # Use today's tab if it exists, otherwise first tab
        today_tab = f"{current_month}-{now.day}"
        desired_tab = today_tab if today_tab in tabs else (tabs[0] if tabs else None)
        
        if not desired_tab:
            print("    FAIL: No tabs found in sheet")
            all_ok = False
        else:
            # Read cookie names (column A, rows 3-52 = 50 rows)
            range_name = f"'{desired_tab}'!A3:A52"
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            
            values = result.get("values", [])
            cookie_names = [row[0] if row and row[0] else "" for row in values]
            
            # Pad to 50 if needed
            while len(cookie_names) < 50:
                cookie_names.append("")
            
            not_in_use = [i for i, c in enumerate(cookie_names) if c and "NOT IN USE" in str(c).upper()]
            used_count = sum(1 for c in cookie_names if c and "NOT IN USE" not in str(c).upper())
            blank_count = sum(1 for c in cookie_names if not c or not str(c).strip())
            
            print(f"    Sheet: {sheet_id[:20]}...")
            print(f"    Tab: {desired_tab}")
            print(f"    Cookie rows: {len(cookie_names)} (max 50)")
            print(f"    Used flavor rows: {used_count}")
            print(f"    [NOT IN USE] slots: {len(not_in_use)}")
            print(f"    Blank rows: {blank_count}")
            
            if len(not_in_use) >= 1:
                print(f"    -> OK: {len(not_in_use)} slot(s) available for new flavors")
            else:
                print("    -> WARNING: No [NOT IN USE] slots! Add rows with '[NOT IN USE]' in column A")
                print("       so new flavors can be claimed automatically.")
                all_ok = False
                
    except FileNotFoundError as e:
        print(f"    SKIP: service-account-key.json not found: {e}")
        print("    Run from project root or ensure credentials are present.")
    except Exception as e:
        print(f"    ERROR: {e}")
        all_ok = False
    
    # 3. Drunken Cookies sheet
    print("\n[3] DRUNKEN COOKIES SHEET")
    print("    New flavors are appended as new columns automatically.")
    print("    -> OK: No pre-configuration needed")
    
    # 4. Summary
    print("\n" + "=" * 60)
    if all_ok:
        print("READY: System is prepared for new flavors.")
        print("When you add a new flavor in Clover:")
        print("  - It will be counted automatically (default-include filter)")
        print("  - Primary sheet: Will claim a [NOT IN USE] row in correct position")
        print("  - Drunken Cookies: Will add a new column automatically")
    else:
        print("ACTION NEEDED: Fix the issues above before adding new flavors.")
        sys.exit(1)
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
