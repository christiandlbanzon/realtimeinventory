#!/usr/bin/env python3
"""Create VM with exponential backoff retry"""

import os
import sys
import base64
import time

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

PROJECT_ID = "boxwood-chassis-332307"
ZONES_TO_TRY = ["us-central1-a", "us-central1-b", "us-east1-b"]  # Try multiple zones
VM_NAME = "real-time-inventory"
SERVICE_ACCOUNT_FILE = "service-account-key.json"
VM_USER = "banzo"

FILES_TO_DEPLOY = {
    "vm_inventory_updater_fixed.py": "/home/banzo/vm_inventory_updater.py",
    "clover_creds.json": "/home/banzo/clover_creds.json",
    "service-account-key.json": "/home/banzo/service-account-key.json"
}

print("="*80)
print("CREATING VM WITH RETRY LOGIC")
print("="*80)
print("\nDiagnosis shows:")
print("  - Project is ACTIVE")
print("  - API is ENABLED")
print("  - Can READ (list instances)")
print("  - WRITE (create) operations getting 503")
print("\nTrying multiple zones with exponential backoff...\n")

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
config_template = {
    'name': VM_NAME,
    'machineType': None,  # Will be set per zone
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

# Try each zone with retries
max_retries_per_zone = 3
success = False

for zone in ZONES_TO_TRY:
    print(f"\nTrying zone: {zone}")
    config = config_template.copy()
    config['machineType'] = f"zones/{zone}/machineTypes/e2-micro"
    
    for attempt in range(max_retries_per_zone):
        try:
            wait_time = (attempt + 1) * 5  # 5, 10, 15 seconds
            if attempt > 0:
                print(f"  Retry {attempt + 1}/{max_retries_per_zone} (waiting {wait_time}s)...")
                time.sleep(wait_time)
            else:
                print(f"  Attempt {attempt + 1}/{max_retries_per_zone}...")
            
            operation = compute.instances().insert(
                project=PROJECT_ID,
                zone=zone,
                body=config
            ).execute()
            
            print("\n" + "="*80)
            print("SUCCESS!")
            print("="*80)
            print(f"\nVM Instance creation initiated!")
            print(f"Zone: {zone}")
            print(f"Operation ID: {operation['name']}")
            print(f"\nThe instance will be created in 2-5 minutes.")
            print(f"\nCheck status:")
            print(f"  python check_vm_creation_status.py")
            success = True
            break
            
        except Exception as e:
            error_str = str(e)
            if "503" in error_str or "unavailable" in error_str.lower():
                if attempt < max_retries_per_zone - 1:
                    continue  # Retry
                else:
                    print(f"  Failed after {max_retries_per_zone} attempts (503 errors)")
                    break  # Try next zone
            elif "already exists" in error_str.lower():
                print(f"  VM already exists in this zone!")
                print(f"  Check: python check_vm_creation_status.py")
                success = True
                break
            else:
                print(f"  ERROR: {e}")
                break  # Try next zone
    
    if success:
        break

if not success:
    print("\n" + "="*80)
    print("FAILED TO CREATE VM")
    print("="*80)
    print("\nTried all zones with retries but still getting 503 errors.")
    print("This appears to be a Google Cloud service issue affecting instance creation.")
    print("\nOptions:")
    print("1. Wait 15-30 minutes and try again")
    print("2. Try via Google Cloud Console: https://console.cloud.google.com/compute/instances")
    print("3. Check status: https://status.cloud.google.com/")
    sys.exit(1)
