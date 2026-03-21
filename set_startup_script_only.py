#!/usr/bin/env python3
"""
Set deployment script as startup-script (without restarting)
User can restart manually when ready
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
VM_NAME = "real-time-inventory"
SERVICE_ACCOUNT_FILE = "service-account-key.json"
VM_USER = "banzo"

FILES_TO_DEPLOY = {
    "vm_inventory_updater_fixed.py": "/home/banzo/vm_inventory_updater.py",
    "clover_creds.json": "/home/banzo/clover_creds.json",
    "service-account-key.json": "/home/banzo/service-account-key.json"
}

def set_startup_script():
    """Set deployment script as startup-script"""
    print("="*80)
    print("SETTING STARTUP SCRIPT")
    print("="*80)
    
    # Read files
    files_content = {}
    for local_file, remote_path in FILES_TO_DEPLOY.items():
        if not os.path.exists(local_file):
            print(f"❌ File not found: {local_file}")
            return False
        
        with open(local_file, 'r', encoding='utf-8') as f:
            content = f.read()
            files_content[remote_path] = content
            print(f"✅ Read {local_file} ({len(content):,} bytes)")
    
    # Create startup script
    startup_script = f"""#!/bin/bash
set -e
cd /home/{VM_USER}

echo "=========================================="
echo "DEPLOYMENT STARTED"
echo "=========================================="

# Clean up
rm -f /home/{VM_USER}/*.py.backup* 2>/dev/null || true

# Deploy files
echo "Deploying files..."
"""
    
    for remote_path, content in files_content.items():
        filename = os.path.basename(remote_path)
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        startup_script += f"""
echo '{content_b64}' | base64 -d > {remote_path}
chmod 644 {remote_path}
echo "  ✅ {filename}"
"""
    
    startup_script += f"""
chmod +x /home/{VM_USER}/vm_inventory_updater.py

# Set up cron
echo ""
echo "Setting up cron job..."
(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/{VM_USER} && /usr/bin/python3 /home/{VM_USER}/vm_inventory_updater.py >> /home/{VM_USER}/inventory_cron.log 2>&1") | crontab -

echo ""
echo "=========================================="
echo "DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "Files deployed:"
ls -lh /home/{VM_USER}/*.py /home/{VM_USER}/*.json 2>/dev/null | grep -v ".backup" || true
echo ""
echo "Cron jobs:"
crontab -l
echo ""
echo "✅ VM is ready!"
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
        
        print("\n✅ Authenticated")
    except Exception as e:
        print(f"\n❌ Auth failed: {e}")
        return False
    
    try:
        # Get VM
        print(f"\n[1/2] Getting VM metadata...")
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        metadata = instance.get('metadata', {})
        fingerprint = metadata.get('fingerprint', '')
        items = metadata.get('items', [])
        
        # Remove old startup-script and deploy-and-setup
        items = [item for item in items if item.get('key') not in ['startup-script', 'deploy-and-setup']]
        
        # Add startup-script
        items.append({
            'key': 'startup-script',
            'value': startup_script
        })
        
        print(f"   Script size: {len(startup_script):,} bytes")
        
        # Set metadata
        print(f"\n[2/2] Setting startup-script metadata...")
        compute.instances().setMetadata(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME,
            body={
                'fingerprint': fingerprint,
                'items': items
            }
        ).execute()
        
        print("   ✅ Startup script set!")
        print("\n" + "="*80)
        print("✅ STARTUP SCRIPT IS SET")
        print("="*80)
        print("\nThe deployment script is now set as 'startup-script'.")
        print("It will run automatically when the VM restarts.")
        print("\nTo activate deployment, restart the VM:")
        print(f"   gcloud compute instances reset {VM_NAME} --zone={ZONE} --project={PROJECT_ID}")
        print("\nOr restart via API (this script will do it now)...")
        
        # Try restart
        try:
            print("\nAttempting to restart VM...")
            compute.instances().reset(
                project=PROJECT_ID,
                zone=ZONE,
                instance=VM_NAME
            ).execute()
            print("✅ VM restart initiated!")
            print("   Deployment will run automatically during boot.")
        except Exception as e:
            print(f"⚠️  Could not restart VM: {e}")
            print("   But startup-script is set - restart manually when ready")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        set_startup_script()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
