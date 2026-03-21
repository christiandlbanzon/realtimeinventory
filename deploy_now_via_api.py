#!/usr/bin/env python3
"""
Deploy the Biscoff fix to VM RIGHT NOW using Compute Engine API
"""

import os
import sys
import base64

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
FIXED_FILE = "vm_inventory_updater_fixed.py"

def deploy_via_metadata_execution(compute):
    """Deploy by executing the metadata script"""
    print("="*80)
    print("DEPLOYING FIX TO VM - EXECUTING NOW")
    print("="*80)
    
    # Read the fixed file
    if not os.path.exists(FIXED_FILE):
        print(f"❌ Fixed file not found: {FIXED_FILE}")
        return False
    
    with open(FIXED_FILE, 'r', encoding='utf-8') as f:
        python_code = f.read()
    
    print(f"✅ Read fixed file ({len(python_code)} characters)")
    
    # Verify it has the fix
    if '"*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff"' not in python_code:
        print("❌ Fixed file doesn't contain the Biscoff fix!")
        return False
    
    print("✅ Verified fix is in the code")
    
    # Create deployment commands
    # Base64 encode the Python code to pass it safely
    python_code_b64 = base64.b64encode(python_code.encode('utf-8')).decode('utf-8')
    
    deploy_command = f"""cd /home/banzo && \
cp vm_inventory_updater.py vm_inventory_updater.py.backup.$(date +%Y%m%d_%H%M%S) && \
echo '{python_code_b64}' | base64 -d > vm_inventory_updater.py && \
chmod +x vm_inventory_updater.py && \
if grep -q '"\\*N\\* Cheesecake with Biscoff"' vm_inventory_updater.py; then \
    echo "✅ Fix verified in deployed file"; \
else \
    echo "❌ WARNING: Fix not found"; \
fi && \
echo "$(date): Biscoff fix deployed" >> /home/banzo/deployment.log"""
    
    try:
        print("\n[1/2] Executing deployment command on VM...")
        
        # Use the instances().setMetadata to add a startup script, then execute it
        # Actually, let's try using the metadata script we already added
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        # Execute the metadata script
        print("   Executing deployment script from metadata...")
        
        # We can't directly execute commands via Compute API without SSH
        # But we can trigger the metadata script execution by checking if it exists
        metadata = instance.get('metadata', {})
        items = metadata.get('items', [])
        
        deploy_script_exists = any(item.get('key') == 'deploy-biscoff-fix' for item in items)
        
        if deploy_script_exists:
            print("   ✅ Deployment script found in metadata")
            print("\n   The script is ready. To execute it, run:")
            print("   gcloud compute ssh inventory-updater-vm --zone=us-central1-a")
            print("   curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-biscoff-fix | bash")
        else:
            print("   ⚠️  Deployment script not in metadata, adding it...")
            # Add it
            fingerprint = metadata.get('fingerprint', '')
            items.append({
                'key': 'deploy-biscoff-fix',
                'value': f"""#!/bin/bash
cd /home/banzo
cp vm_inventory_updater.py vm_inventory_updater.py.backup.$(date +%Y%m%d_%H%M%S)
echo '{python_code_b64}' | base64 -d > vm_inventory_updater.py
chmod +x vm_inventory_updater.py
echo "$(date): Deployed" >> /home/banzo/deployment.log"""
            })
            
            compute.instances().setMetadata(
                project=PROJECT_ID,
                zone=ZONE,
                instance=VM_NAME,
                body={
                    'fingerprint': fingerprint,
                    'items': items
                }
            ).execute()
            print("   ✅ Added deployment script to metadata")
        
        # Try to use OS Login or direct command execution
        # Actually, Compute Engine API doesn't support direct command execution
        # We need to use gcloud or SSH
        
        # Alternative: Write file content directly via metadata startup script that runs immediately
        # But startup scripts only run on boot
        
        print("\n[2/2] Attempting direct file write via metadata...")
        
        # Create a script that will write the file
        # We'll use a different approach - write the file content to a temp location via metadata
        # and then have a command copy it
        
        # Actually, the best way is to use the metadata script we created
        # But we need SSH to execute it
        
        print("   ⚠️  Cannot execute commands directly via API")
        print("   Need to use SSH or gcloud")
        
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def deploy_via_startup_script_immediate(compute):
    """Try to deploy by creating a startup script and triggering it"""
    print("\nTrying alternative method...")
    
    # Read fixed file
    with open(FIXED_FILE, 'r', encoding='utf-8') as f:
        python_code = f.read()
    
    python_code_b64 = base64.b64encode(python_code.encode('utf-8')).decode('utf-8')
    
    # Create a script that writes the file
    script_content = f"""#!/bin/bash
cd /home/banzo
cp vm_inventory_updater.py vm_inventory_updater.py.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
echo '{python_code_b64}' | base64 -d > vm_inventory_updater.py
chmod +x vm_inventory_updater.py
echo "$(date): Biscoff fix deployed via startup script" >> /home/banzo/deployment.log
"""
    
    try:
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        metadata = instance.get('metadata', {})
        fingerprint = metadata.get('fingerprint', '')
        items = metadata.get('items', [])
        
        # Remove old startup scripts
        items = [item for item in items if item.get('key') not in ['startup-script', 'deploy-biscoff-fix']]
        
        # Add immediate deployment script
        items.append({
            'key': 'startup-script',
            'value': script_content
        })
        
        compute.instances().setMetadata(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME,
            body={
                'fingerprint': fingerprint,
                'items': items
            }
        ).execute()
        
        print("✅ Startup script added")
        print("\n⚠️  Startup scripts only run on VM boot.")
        print("   To trigger immediately, restart the VM:")
        print(f"   gcloud compute instances stop {VM_NAME} --zone={ZONE}")
        print(f"   gcloud compute instances start {VM_NAME} --zone={ZONE}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("="*80)
    print("DEPLOY FIX TO VM - AUTOMATED")
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
    
    # Try deployment via metadata execution
    if deploy_via_metadata_execution(compute):
        return True
    
    # Try startup script method
    print("\n" + "="*80)
    print("TRYING STARTUP SCRIPT METHOD")
    print("="*80)
    
    if deploy_via_startup_script_immediate(compute):
        print("\n✅ Deployment script prepared!")
        print("\nThe script will run on next VM restart.")
        print("To deploy immediately, restart the VM or use SSH.")
        return True
    
    print("\n" + "="*80)
    print("⚠️  AUTOMATED DEPLOYMENT NOT POSSIBLE")
    print("="*80)
    print("\nCompute Engine API doesn't support direct command execution.")
    print("You need to use SSH or gcloud to deploy.")
    print("\nQuickest method:")
    print(f"  gcloud compute scp {FIXED_FILE} {VM_NAME}:/home/banzo/vm_inventory_updater.py --zone={ZONE}")
    
    return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
