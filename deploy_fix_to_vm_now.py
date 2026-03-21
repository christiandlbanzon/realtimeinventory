#!/usr/bin/env python3
"""
Deploy the Biscoff fix to VM using Compute Engine API
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

def deploy_via_metadata(compute):
    """Deploy fix via VM metadata startup script"""
    print("="*80)
    print("DEPLOYING FIX TO VM VIA METADATA")
    print("="*80)
    
    # Read the fixed file
    fixed_file = "vm_inventory_updater_fixed.py"
    if not os.path.exists(fixed_file):
        print(f"❌ Fixed file not found: {fixed_file}")
        return False
    
    with open(fixed_file, 'r', encoding='utf-8') as f:
        python_code = f.read()
    
    print(f"✅ Read fixed file ({len(python_code)} characters)")
    
    # Verify it has the fix
    if '"*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff"' not in python_code:
        print("❌ Fixed file doesn't contain the Biscoff fix!")
        return False
    
    print("✅ Verified fix is in the code")
    
    # Create deployment script
    deploy_script = f"""#!/bin/bash
cd /home/banzo

# Backup current file
if [ -f vm_inventory_updater.py ]; then
    cp vm_inventory_updater.py vm_inventory_updater.py.backup.$(date +%Y%m%d_%H%M%S)
    echo "Backup created: vm_inventory_updater.py.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Write new file
cat > vm_inventory_updater.py << 'PYTHONEOF'
{python_code}
PYTHONEOF

# Set permissions
chmod +x vm_inventory_updater.py

# Verify the fix is there
if grep -q '"\\*N\\* Cheesecake with Biscoff"' vm_inventory_updater.py; then
    echo "✅ Fix verified in deployed file"
else
    echo "❌ WARNING: Fix not found in deployed file"
fi

# Log deployment
echo "$(date): Biscoff fix deployed via metadata" >> /home/banzo/deployment.log
"""
    
    try:
        # Get current instance info
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        # Get current metadata
        metadata = instance.get('metadata', {})
        fingerprint = metadata.get('fingerprint', '')
        items = metadata.get('items', [])
        
        # Remove old deployment scripts
        items = [item for item in items if item.get('key') not in ['deploy-biscoff-fix', 'startup-script']]
        
        # Add deployment script to metadata
        items.append({
            'key': 'deploy-biscoff-fix',
            'value': deploy_script
        })
        
        # Update metadata
        print("\n[1/2] Updating VM metadata...")
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
        print("\n⚠️  IMPORTANT: The VM needs to be restarted for the metadata script to run automatically.")
        print("   OR you can SSH and run it manually:")
        print(f"\n   gcloud compute ssh {VM_NAME} --zone={ZONE}")
        print("   Then run:")
        print("   curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-biscoff-fix | bash")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*80)
    print("DEPLOY BISCOFF FIX TO VM")
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
    
    # Deploy
    success = deploy_via_metadata(compute)
    
    if success:
        print("\n" + "="*80)
        print("DEPLOYMENT INSTRUCTIONS")
        print("="*80)
        print("\nThe deployment script has been added to VM metadata.")
        print("\nTo complete deployment, choose one:")
        print("\nOption 1: SSH and run manually (Recommended):")
        print(f"  gcloud compute ssh {VM_NAME} --zone={ZONE}")
        print("  curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-biscoff-fix | bash")
        print("\nOption 2: Restart VM (will run automatically):")
        print(f"  gcloud compute instances stop {VM_NAME} --zone={ZONE}")
        print(f"  gcloud compute instances start {VM_NAME} --zone={ZONE}")
        print("\nOption 3: Use gcloud scp directly:")
        print(f"  gcloud compute scp vm_inventory_updater_fixed.py {VM_NAME}:/home/banzo/vm_inventory_updater.py --zone={ZONE}")
    
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
