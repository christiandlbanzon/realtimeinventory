#!/usr/bin/env python3
"""
Quick deployment - tries once, reports status immediately
"""

import os
import sys
import base64

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

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

print("="*80)
print("QUICK DEPLOYMENT VIA API")
print("="*80)

# Read files
files_content = {}
for local_file, remote_path in FILES_TO_DEPLOY.items():
    if not os.path.exists(local_file):
        print(f"❌ File not found: {local_file}")
        sys.exit(1)
    with open(local_file, 'r', encoding='utf-8') as f:
        files_content[remote_path] = f.read()
    print(f"✅ {local_file}")

# Build startup script
startup_script = f"""#!/bin/bash
set -e
cd /home/{VM_USER}
echo "Deployment started at $(date)"
"""
for remote_path, content in files_content.items():
    filename = os.path.basename(remote_path)
    content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    startup_script += f"""
echo '{content_b64}' | base64 -d > {remote_path}
chmod 644 {remote_path}
echo "✅ {filename}"
"""
startup_script += f"""
chmod +x /home/{VM_USER}/vm_inventory_updater.py
(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/{VM_USER} && /usr/bin/python3 /home/{VM_USER}/vm_inventory_updater.py >> /home/{VM_USER}/inventory_cron.log 2>&1") | crontab -
echo "✅ Deployment complete"
ls -lh /home/{VM_USER}/*.py /home/{VM_USER}/*.json 2>/dev/null | grep -v ".backup" || true
"""

# Authenticate and deploy
try:
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/compute']
    )
    http = httplib2.Http(proxy_info=None)
    authorized_http = AuthorizedHttp(credentials, http=http)
    compute = build('compute', 'v1', http=authorized_http)
    
    print("\n✅ Authenticated")
    
    instance = compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=VM_NAME).execute()
    metadata = instance.get('metadata', {})
    fingerprint = metadata.get('fingerprint', '')
    items = [item for item in metadata.get('items', []) if item.get('key') != 'startup-script']
    items.append({'key': 'startup-script', 'value': startup_script})
    
    print("Setting startup-script...")
    compute.instances().setMetadata(
        project=PROJECT_ID,
        zone=ZONE,
        instance=VM_NAME,
        body={'fingerprint': fingerprint, 'items': items}
    ).execute()
    
    print("✅ Startup script set!")
    print("Restarting VM...")
    compute.instances().reset(project=PROJECT_ID, zone=ZONE, instance=VM_NAME).execute()
    print("✅ VM restart initiated!")
    print("\n✅ Deployment will run automatically when VM restarts")
    
except Exception as e:
    error_msg = str(e)
    if "503" in error_msg:
        print(f"\n⚠️  Google Cloud API returned 503 (temporary backend issue)")
        print("This is a temporary Google Cloud problem, not a code issue.")
        print("The deployment script is ready - try again in a few minutes.")
    else:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
