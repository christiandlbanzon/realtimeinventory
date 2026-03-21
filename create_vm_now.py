#!/usr/bin/env python3
"""Create VM immediately without waiting"""

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
print("CREATING VM: real-time-inventory")
print("="*80)

# Read files
print("\nReading files...")
files_content = {}
for local_file, remote_path in FILES_TO_DEPLOY.items():
    if not os.path.exists(local_file):
        print(f"ERROR: {local_file} not found!")
        sys.exit(1)
    with open(local_file, 'r', encoding='utf-8') as f:
        files_content[remote_path] = f.read()
    print(f"  OK: {local_file}")

# Verify February sheet ID
if "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4" in files_content["/home/banzo/vm_inventory_updater.py"]:
    print("  OK: February sheet ID verified")
else:
    print("  WARNING: February sheet ID not found!")

# Build startup script
print("\nBuilding startup script...")
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
print("\nAuthenticating...")
try:
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/compute']
    )
    http = httplib2.Http(proxy_info=None)
    authorized_http = AuthorizedHttp(credentials, http=http)
    compute = build('compute', 'v1', http=authorized_http)
    print("  OK: Authenticated")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# Create VM config
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

# Create VM with retry logic
print("\nCreating VM (this may take a moment)...")
max_retries = 5
operation = None

for attempt in range(max_retries):
    try:
        print(f"  Attempt {attempt + 1}/{max_retries}...")
        operation = compute.instances().insert(
            project=PROJECT_ID,
            zone=ZONE,
            body=config
        ).execute()
        break  # Success!
        
    except Exception as e:
        error_str = str(e)
        if attempt < max_retries - 1:
            if "503" in error_str or "unavailable" in error_str.lower() or "backendError" in error_str:
                wait_time = (attempt + 1) * 10  # 10, 20, 30, 40 seconds
                print(f"  API temporarily unavailable (503), waiting {wait_time}s before retry...")
                import time
                time.sleep(wait_time)
                continue
            else:
                # Other error, don't retry
                raise
        else:
            # Last attempt failed
            raise

if operation:
    print("="*80)
    print("SUCCESS!")
    print("="*80)
    print(f"\nVM creation initiated!")
    print(f"Operation ID: {operation['name']}")
    print(f"\nThe VM will be created in 2-5 minutes.")
    print(f"The startup script will automatically:")
    print(f"  - Install dependencies")
    print(f"  - Deploy all files")
    print(f"  - Set up cron (runs every 5 minutes)")
    print(f"\nCheck status:")
    print(f"  python check_vm_creation_status.py")
    print(f"\nOr in Google Cloud Console:")
    print(f"  https://console.cloud.google.com/compute/instances?project={PROJECT_ID}")
else:
    print("\nERROR: Failed to create VM after all retries")
    sys.exit(1)
