#!/usr/bin/env python3
"""
Deploy files using Compute Engine API - no gcloud CLI needed
Uses service account authentication directly
"""

import os
import sys
import base64
import time

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

def deploy_via_api():
    """Deploy files using Compute Engine API"""
    print("="*80)
    print("DEPLOYING VIA COMPUTE ENGINE API")
    print("="*80)
    print("Using service account - no gcloud CLI needed")
    print()
    
    # Read files
    files_content = {}
    for local_file, remote_path in FILES_TO_DEPLOY.items():
        if not os.path.exists(local_file):
            print(f"❌ File not found: {local_file}")
            return False
        with open(local_file, 'r', encoding='utf-8') as f:
            files_content[remote_path] = f.read()
            print(f"✅ Read {local_file} ({len(files_content[remote_path]):,} bytes)")
    
    # Create startup script
    startup_script = f"""#!/bin/bash
set -e
cd /home/{VM_USER}

echo "=========================================="
echo "DEPLOYMENT STARTED"
echo "=========================================="
echo "Timestamp: $(date)"
echo ""

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
    print("\n[1/3] Authenticating...")
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/compute']
        )
        http = httplib2.Http(proxy_info=None)
        authorized_http = AuthorizedHttp(credentials, http=http)
        compute = build('compute', 'v1', http=authorized_http)
        print("   ✅ Authenticated")
    except Exception as e:
        print(f"   ❌ Auth failed: {e}")
        return False
    
    # Get VM and set metadata
    print("\n[2/3] Setting startup-script metadata...")
    try:
        instance = compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=VM_NAME).execute()
        metadata = instance.get('metadata', {})
        fingerprint = metadata.get('fingerprint', '')
        items = [item for item in metadata.get('items', []) if item.get('key') not in ['startup-script', 'deploy-and-setup']]
        items.append({'key': 'startup-script', 'value': startup_script})
        
        # Retry with exponential backoff
        max_retries = 10
        for attempt in range(max_retries):
            try:
                compute.instances().setMetadata(
                    project=PROJECT_ID,
                    zone=ZONE,
                    instance=VM_NAME,
                    body={'fingerprint': fingerprint, 'items': items}
                ).execute()
                print("   ✅ Startup script set!")
                break
            except Exception as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    wait = min((attempt + 1) * 2, 10)
                    print(f"   ⏳ 503 error (attempt {attempt + 1}/{max_retries}), waiting {wait}s...")
                    time.sleep(wait)
                    instance = compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=VM_NAME).execute()
                    fingerprint = instance.get('metadata', {}).get('fingerprint', '')
                else:
                    print(f"   ❌ Error: {e}")
                    if "503" not in str(e):
                        raise
        else:
            print("   ❌ Failed after retries")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Restart VM
    print("\n[3/3] Restarting VM to trigger deployment...")
    try:
        compute.instances().reset(project=PROJECT_ID, zone=ZONE, instance=VM_NAME).execute()
        print("   ✅ VM restart initiated!")
        print("\n✅ Deployment will run automatically when VM restarts")
        print("   (startup script executes on boot)")
        return True
    except Exception as e:
        if "503" in str(e):
            print(f"   ⚠️  503 error, but startup-script is set")
            print("   It will run on next manual restart")
            return True
        print(f"   ❌ Error: {e}")
        return False

if __name__ == "__main__":
    try:
        success = deploy_via_api()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
