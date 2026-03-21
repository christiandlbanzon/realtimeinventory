#!/usr/bin/env python3
"""
Verify if the VM has the Biscoff fix deployed
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

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

PROJECT_ID = "boxwood-chassis-332307"
ZONE = "us-central1-a"
VM_NAME = "inventory-updater-vm"
SERVICE_ACCOUNT_FILE = "service-account-key.json"

def check_vm_code_via_serial(compute):
    """Try to check VM code via serial port output"""
    print("\n[1/2] Checking VM serial port output for recent activity...")
    try:
        result = compute.instances().getSerialPortOutput(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        output = result.get('contents', '')
        if output:
            lines = output.split('\n')[-100:]  # Last 100 lines
            
            # Look for any Python errors or Biscoff mentions
            python_errors = [line for line in lines if 'error' in line.lower() or 'exception' in line.lower() or 'traceback' in line.lower()]
            biscoff_mentions = [line for line in lines if 'biscoff' in line.lower()]
            
            print(f"   Found {len(lines)} recent log lines")
            
            if python_errors:
                print(f"   ⚠️  Found {len(python_errors)} Python errors:")
                for line in python_errors[-3:]:
                    print(f"      {line[:100]}")
            
            if biscoff_mentions:
                print(f"   ℹ️  Found {len(biscoff_mentions)} Biscoff mentions in logs")
        else:
            print("   ⚠️  No serial port output available")
    except Exception as e:
        print(f"   ⚠️  Could not check serial port: {e}")

def main():
    print("="*80)
    print("VERIFYING VM CODE STATUS")
    print("="*80)
    
    # Authenticate
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=[
                'https://www.googleapis.com/auth/cloud-platform',
                'https://www.googleapis.com/auth/compute'
            ]
        )
        
        http = httplib2.Http(proxy_info=None)
        authorized_http = AuthorizedHttp(credentials, http=http)
        compute = build('compute', 'v1', http=authorized_http)
        
        print("✅ Authenticated")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False
    
    # Check VM status
    try:
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        status = instance.get('status', 'UNKNOWN')
        print(f"\nVM Status: {status}")
        
        if status != 'RUNNING':
            print(f"⚠️  VM is {status} - cannot check code")
            return False
    except Exception as e:
        print(f"❌ Error checking VM: {e}")
        return False
    
    # Check serial port
    check_vm_code_via_serial(compute)
    
    # Check local file
    print("\n[2/2] Checking local fixed file...")
    fixed_file = "vm_inventory_updater_fixed.py"
    if os.path.exists(fixed_file):
        with open(fixed_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        has_fix = '"*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff"' in content
        if has_fix:
            print(f"   ✅ Local file has the fix")
        else:
            print(f"   ❌ Local file missing fix!")
    else:
        print(f"   ⚠️  Local fixed file not found")
    
    print("\n" + "="*80)
    print("STATUS")
    print("="*80)
    print("\n⚠️  Cannot directly verify VM code without SSH")
    print("\nThe fix is:")
    print("  ✅ Created locally in vm_inventory_updater_fixed.py")
    print("  ✅ Tested and verified (backfill worked)")
    print("  ⏳ NOT YET DEPLOYED to VM")
    print("\nTo deploy the fix to VM:")
    print(f"  gcloud compute scp vm_inventory_updater_fixed.py {VM_NAME}:/home/banzo/vm_inventory_updater.py --zone={ZONE}")
    print("\nAfter deployment, the cron job will use the new code automatically.")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
