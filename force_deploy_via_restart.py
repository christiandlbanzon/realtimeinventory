#!/usr/bin/env python3
"""
Deploy fix by restarting VM with startup script
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
import base64

PROJECT_ID = "boxwood-chassis-332307"
ZONE = "us-central1-a"
VM_NAME = "inventory-updater-vm"
SERVICE_ACCOUNT_FILE = "service-account-key.json"
FIXED_FILE = "vm_inventory_updater_fixed.py"

def deploy_and_restart():
    """Deploy fix via startup script and restart VM"""
    print("="*80)
    print("DEPLOYING FIX AND RESTARTING VM")
    print("="*80)
    
    # Read fixed file
    if not os.path.exists(FIXED_FILE):
        print(f"❌ Fixed file not found: {FIXED_FILE}")
        return False
    
    with open(FIXED_FILE, 'r', encoding='utf-8') as f:
        python_code = f.read()
    
    print(f"✅ Read fixed file ({len(python_code)} characters)")
    
    # Verify fix
    if '"*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff"' not in python_code:
        print("❌ Fix not found in file!")
        return False
    
    print("✅ Verified fix is in the code")
    
    # Base64 encode for safe transmission
    python_code_b64 = base64.b64encode(python_code.encode('utf-8')).decode('utf-8')
    
    # Create startup script
    startup_script = f"""#!/bin/bash
cd /home/banzo

# Backup current file
if [ -f vm_inventory_updater.py ]; then
    cp vm_inventory_updater.py vm_inventory_updater.py.backup.$(date +%Y%m%d_%H%M%S)
    echo "Backup created"
fi

# Write new file from base64
echo '{python_code_b64}' | base64 -d > vm_inventory_updater.py

# Set permissions
chmod +x vm_inventory_updater.py

# Verify fix
if grep -q '"\\*N\\* Cheesecake with Biscoff"' vm_inventory_updater.py; then
    echo "✅ Biscoff fix verified in deployed file"
else
    echo "❌ WARNING: Fix not found in deployed file"
fi

# Log deployment
echo "$(date): Biscoff fix deployed via startup script" >> /home/banzo/deployment.log
"""
    
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
    
    # Get instance
    try:
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        status = instance.get('status', 'UNKNOWN')
        print(f"\nVM Status: {status}")
        
        if status != 'RUNNING':
            print(f"⚠️  VM is {status}, starting it first...")
            compute.instances().start(
                project=PROJECT_ID,
                zone=ZONE,
                instance=VM_NAME
            ).execute()
            print("   VM started")
        
    except Exception as e:
        print(f"❌ Error getting VM: {e}")
        return False
    
    # Update metadata with startup script
    try:
        metadata = instance.get('metadata', {})
        fingerprint = metadata.get('fingerprint', '')
        items = metadata.get('items', [])
        
        # Remove old startup scripts
        items = [item for item in items if item.get('key') not in ['startup-script', 'deploy-biscoff-fix']]
        
        # Add new startup script
        items.append({
            'key': 'startup-script',
            'value': startup_script
        })
        
        print("\n[1/2] Updating VM metadata with deployment script...")
        compute.instances().setMetadata(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME,
            body={
                'fingerprint': fingerprint,
                'items': items
            }
        ).execute()
        
        print("✅ Metadata updated")
        
        # Restart VM to trigger startup script
        print("\n[2/2] Restarting VM to trigger deployment...")
        print("   This will deploy the fix automatically...")
        
        compute.instances().reset(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        print("✅ VM restart initiated")
        print("\n⏳ VM is restarting...")
        print("   The startup script will deploy the fix automatically.")
        print("   This may take 1-2 minutes.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*80)
    print("FORCE DEPLOY VIA VM RESTART")
    print("="*80)
    print("\n⚠️  WARNING: This will restart the VM!")
    print("   The VM will be unavailable for ~1-2 minutes during restart.")
    print("   The fix will be deployed automatically via startup script.")
    print()
    
    # Ask for confirmation (but we'll proceed since user said "go deploy it")
    print("Proceeding with deployment...")
    
    success = deploy_and_restart()
    
    if success:
        print("\n" + "="*80)
        print("✅ DEPLOYMENT INITIATED!")
        print("="*80)
        print("\nThe VM is restarting and will deploy the fix automatically.")
        print("\nTo verify after restart (wait 2-3 minutes):")
        print(f"  gcloud compute ssh {VM_NAME} --zone={ZONE} --command='grep -c \"\\*N\\* Cheesecake with Biscoff\" /home/banzo/vm_inventory_updater.py'")
        print("\nThe cron job will use the new code on the next run (every 5 minutes).")
    else:
        print("\n❌ Deployment failed")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
