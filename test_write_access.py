#!/usr/bin/env python3
"""
Test write access to February sheet
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

def test_write_access():
    """Test if service account can write to February sheet"""
    print("="*80)
    print("TESTING WRITE ACCESS TO FEBRUARY SHEET")
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
        
        # Test write access by trying to write to a test cell
        print("\n[1/2] Testing write access...")
        test_range = "Z999"  # Use a cell that's unlikely to have data
        
        try:
            # Try to write a test value
            result = service.spreadsheets().values().update(
                spreadsheetId=FEBRUARY_SHEET_ID,
                range=test_range,
                valueInputOption='USER_ENTERED',
                body={
                    'values': [['TEST_WRITE_ACCESS']]
                }
            ).execute()
            
            print("✅ Write access works!")
            print(f"   Updated {result.get('updatedCells', 0)} cell(s)")
            
            # Clean up - delete the test value
            print("\n[2/2] Cleaning up test value...")
            service.spreadsheets().values().clear(
                spreadsheetId=FEBRUARY_SHEET_ID,
                range=test_range
            ).execute()
            print("✅ Test value removed")
            
            print("\n" + "="*80)
            print("✅ WRITE ACCESS VERIFIED!")
            print("="*80)
            print("\nThe service account has Editor access and can:")
            print("  ✅ Read from the sheet")
            print("  ✅ Write to the sheet")
            print("  ✅ Update cells")
            print("  ✅ Create tabs if needed")
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            if "PERMISSION_DENIED" in error_msg or "permission" in error_msg.lower():
                print(f"\n❌ PERMISSION DENIED - Write access not available!")
                print(f"\n⚠️  The sheet needs to be shared with Editor permissions.")
                print(f"\n📧 Share the February sheet with this email:")
                print(f"   {SERVICE_ACCOUNT_EMAIL}")
                print(f"\n📋 Steps:")
                print(f"   1. Open the February sheet:")
                print(f"      https://docs.google.com/spreadsheets/d/{FEBRUARY_SHEET_ID}/edit")
                print(f"   2. Click 'Share' button")
                print(f"   3. Add: {SERVICE_ACCOUNT_EMAIL}")
                print(f"   4. Give 'Editor' permissions (not Viewer)")
                print(f"   5. Click 'Send'")
                print(f"\n⚠️  Without Editor access, the VM cannot update sales data!")
                return False
            else:
                print(f"❌ Error testing write: {e}")
                return False
        
    except FileNotFoundError:
        print(f"❌ Service account file not found: {SERVICE_ACCOUNT_FILE}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_write_access()
    sys.exit(0 if success else 1)
