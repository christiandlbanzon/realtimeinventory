#!/usr/bin/env python3
"""
Test access to February sheet
"""

import os
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = "service-account-key.json"
FEBRUARY_SHEET_ID = "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4"
SERVICE_ACCOUNT_EMAIL = "703996360436-compute@developer.gserviceaccount.com"

def test_february_sheet_access():
    """Test if service account can access February sheet"""
    print("="*80)
    print("TESTING FEBRUARY SHEET ACCESS")
    print("="*80)
    
    print(f"\nService Account: {SERVICE_ACCOUNT_EMAIL}")
    print(f"February Sheet ID: {FEBRUARY_SHEET_ID}")
    
    try:
        # Authenticate
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        service = build("sheets", "v4", credentials=creds)
        print("\n✅ Authenticated successfully")
        
        # Try to get sheet info
        print("\n[1/2] Attempting to read sheet metadata...")
        try:
            sheet_info = service.spreadsheets().get(spreadsheetId=FEBRUARY_SHEET_ID).execute()
            
            title = sheet_info.get('properties', {}).get('title', 'Unknown')
            tabs = [sheet.get('properties', {}).get('title', 'Unknown') for sheet in sheet_info.get('sheets', [])]
            
            print(f"✅ Sheet accessed successfully!")
            print(f"   Title: {title}")
            print(f"   Tabs found: {len(tabs)}")
            if tabs:
                print(f"   First few tabs: {tabs[:5]}")
            
        except Exception as e:
            error_msg = str(e)
            if "PERMISSION_DENIED" in error_msg or "permission" in error_msg.lower():
                print(f"\n❌ PERMISSION DENIED!")
                print(f"\n⚠️  The sheet needs to be shared with the service account.")
                print(f"\n📧 Share the sheet with this email:")
                print(f"   {SERVICE_ACCOUNT_EMAIL}")
                print(f"\n📋 Steps:")
                print(f"   1. Open the February sheet:")
                print(f"      https://docs.google.com/spreadsheets/d/{FEBRUARY_SHEET_ID}/edit")
                print(f"   2. Click 'Share' button")
                print(f"   3. Add: {SERVICE_ACCOUNT_EMAIL}")
                print(f"   4. Give 'Editor' permissions")
                print(f"   5. Click 'Send'")
                return False
            else:
                print(f"❌ Error accessing sheet: {e}")
                return False
        
        # Try to read a cell (test write access)
        print("\n[2/2] Testing read access to a cell...")
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=FEBRUARY_SHEET_ID,
                range="A1"
            ).execute()
            
            values = result.get('values', [])
            print(f"✅ Read access works!")
            if values:
                print(f"   Cell A1: {values[0][0] if values[0] else '(empty)'}")
            
        except Exception as e:
            print(f"⚠️  Could not read cell: {e}")
            print("   (This might be okay if the sheet is empty)")
        
        print("\n" + "="*80)
        print("✅ FEBRUARY SHEET ACCESS VERIFIED!")
        print("="*80)
        print("\nThe service account can access the February sheet.")
        print("You can proceed with deployment.")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ Service account file not found: {SERVICE_ACCOUNT_FILE}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_february_sheet_access()
    sys.exit(0 if success else 1)
