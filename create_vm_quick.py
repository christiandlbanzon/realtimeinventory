#!/usr/bin/env python3
"""Create VM quickly without waiting for retries - just initiate and exit"""

import os
import sys
import base64

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

print("="*80)
print("CREATING VM INSTANCE (quick mode)")
print("="*80)
print("\nNote: 'VM' and 'Instance' are the same thing in Google Cloud")
print("We're creating a Compute Engine instance (which is a VM)\n")

# Read files
print("[1/3] Reading files...")
files_content = {}
for local_file, remote_path in FILES_TO_DEPLOY.items():
    if not os.path.exists(local_file):
        print(f"ERROR: {local_file} not found!")
        sys.exit(1)
    with open(local_file, 'r', encoding='utf-8') as f:
        files_content[remote_path] = f.read()
    print(f"  OK: {local_file}")

if "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4" in files_content["/home/banzo/vm_inventory_updater.py"]:
    print("  OK: February sheet ID verified")

# Build startup script
print("\n[2/3] Building startup script...")
startup_script = f"""#!/bin/bash
set -e
exec > /var/log/startup.log 2>&1
echo "=== Startup Script Started ==="
date

apt-get update -y
apt-get install -y python3 python3-pip git

if ! id -u {VM_USER} &>/dev/null; then
    useradd -m -s /bin/bash {VM_USER}
fi

mkdir -p /home/{VM_USER}
chown -R {VM_USER}:{VM_USER} /home/{VM_USER}

pip3 install --upgrade pip
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests python-dotenv fuzzywuzzy python-Levenshtein

cd /home/{VM_USER}
"""

for remote_path, content in files_content.items():
    filename = os.path.basename(remote_path)
    content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    startup_script += f"echo '{content_b64}' | base64 -d > {remote_path}\n"
    startup_script += f"chmod 644 {remote_path}\n"

startup_script += f"""
chmod +x /home/{VM_USER}/vm_inventory_updater.py
(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/{VM_USER} && /usr/bin/python3 /home/{VM_USER}/vm_inventory_updater.py >> /home/{VM_USER}/inventory_cron.log 2>&1") | crontab -
echo "=== Deployment Complete ==="
date
"""
print(f"  OK: Startup script ({len(startup_script):,} bytes)")

# Authenticate
print("\n[3/3] Creating VM instance...")
try:
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/compute']
    )
    http = httplib2.Http(proxy_info=None)
    authorized_http = AuthorizedHttp(credentials, http=http)
    compute = build('compute', 'v1', http=authorized_http)
except Exception as e:
    print(f"ERROR: Authentication failed: {e}")
    sys.exit(1)

# VM config
config = {
    'name': VM_NAME,
    'machineType': f"zones/{ZONE}/machineTypes/e2-micro",
    'disks': [{
        'boot': True,
        'autoDelete': True,
        'initializeParams': {
            'sourceImage': 'projects/debian-cloud/global/images/family/debian-12',
            'diskSizeGb': '20'
        }
    }],
    'networkInterfaces': [{
        'network': 'global/networks/default',
        'accessConfigs': [{'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}]
    }],
    'serviceAccounts': [{
        'email': 'default',
        'scopes': [
            'https://www.googleapis.com/auth/cloud-platform',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
    }],
    'metadata': {'items': [{'key': 'startup-script', 'value': startup_script}]},
    'tags': {'items': ['inventory-updater']}
}

# Try to create (single attempt, no retries)
try:
    print("  Sending request to Google Cloud...")
    operation = compute.instances().insert(
        project=PROJECT_ID,
        zone=ZONE,
        body=config
    ).execute()
    
    print("\n" + "="*80)
    print("SUCCESS!")
    print("="*80)
    print(f"\nVM Instance creation initiated!")
    print(f"Operation ID: {operation['name']}")
    print(f"\nThe instance will be created in 2-5 minutes.")
    print(f"Name: {VM_NAME}")
    print(f"Zone: {ZONE}")
    print(f"\nThe startup script will automatically:")
    print(f"  - Install dependencies")
    print(f"  - Deploy all files")
    print(f"  - Set up cron (runs every 5 minutes)")
    print(f"\nCheck status:")
    print(f"  python check_vm_creation_status.py")
    
except Exception as e:
    error_str = str(e)
    if "503" in error_str or "unavailable" in error_str.lower():
        print(f"\nWARNING: Google Cloud API is temporarily unavailable (503)")
        print(f"   This is a temporary Google Cloud issue.")
        print(f"   Wait a few minutes and try again.")
        print(f"\n   Error details: {error_str[:200]}")
    else:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    sys.exit(1)
