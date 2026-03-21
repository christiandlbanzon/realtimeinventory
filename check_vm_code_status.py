#!/usr/bin/env python3
"""
Check if the VM has the Biscoff fix deployed
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

def check_vm_code():
    """Check if the VM code has the Biscoff fix"""
    print("="*80)
    print("CHECKING VM CODE STATUS")
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
    
    # Check VM serial port output for recent logs
    print("\n[1/3] Checking VM serial port output...")
    try:
        result = compute.instances().getSerialPortOutput(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        output = result.get('contents', '')
        if output:
            lines = output.split('\n')[-50:]  # Last 50 lines
            print(f"   Found {len(lines)} recent log lines")
            
            # Check for Biscoff-related logs
            biscoff_mentions = [line for line in lines if 'biscoff' in line.lower()]
            if biscoff_mentions:
                print(f"   ⚠️  Found {len(biscoff_mentions)} Biscoff mentions in logs")
                for line in biscoff_mentions[-5:]:
                    print(f"      {line[:80]}")
        else:
            print("   ⚠️  No serial port output available")
    except Exception as e:
        print(f"   ⚠️  Could not check serial port: {e}")
    
    # Try to check the actual file on VM via SSH command
    print("\n[2/3] Checking VM file for Biscoff fix...")
    print("   (This requires SSH access - checking if we can verify via API)")
    
    # We can't directly read files via Compute API, but we can check if VM is running
    try:
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        status = instance.get('status', 'UNKNOWN')
        print(f"   VM Status: {status}")
        
        if status == 'RUNNING':
            print("   ✅ VM is running")
        else:
            print(f"   ⚠️  VM is {status}")
    except Exception as e:
        print(f"   ❌ Error checking VM: {e}")
    
    # Check local fixed file
    print("\n[3/3] Checking local fixed file...")
    fixed_file = "vm_inventory_updater_fixed.py"
    if os.path.exists(fixed_file):
        print(f"   ✅ Local fixed file exists: {fixed_file}")
        
        # Check if it has the fix
        with open(fixed_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if '"*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff"' in content:
            print("   ✅ Local file has the Biscoff fix")
        else:
            print("   ❌ Local file missing Biscoff fix!")
    else:
        print(f"   ⚠️  Local fixed file not found: {fixed_file}")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("\n⚠️  Cannot directly verify VM code without SSH access")
    print("\nTo verify the fix is on the VM, you need to:")
    print("  1. SSH to VM:")
    print(f"     gcloud compute ssh {VM_NAME} --zone={ZONE}")
    print("\n  2. Check the file:")
    print("     grep -c '\"\\*N\\* Cheesecake with Biscoff\"' /home/banzo/vm_inventory_updater.py")
    print("\n  3. Or check recent logs:")
    print("     tail -100 /home/banzo/inventory_cron.log | grep -i biscoff")
    print("\nTo deploy the fix:")
    print(f"  gcloud compute scp vm_inventory_updater_fixed.py {VM_NAME}:/home/banzo/vm_inventory_updater.py --zone={ZONE}")
    
    return True

if __name__ == "__main__":
    try:
        check_vm_code()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
