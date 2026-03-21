#!/usr/bin/env python3
"""
Create a fresh VM in a different zone with everything configured correctly
This avoids us-central1 issues and sets up everything from scratch
"""

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
# Use a different zone to avoid us-central1 issues
ZONE = "us-east1-b"  # East coast - different region entirely
VM_NAME = "real-time-inventory-v2"  # New name to avoid conflicts
SERVICE_ACCOUNT_FILE = "service-account-key.json"
VM_USER = "banzo"

FILES_TO_DEPLOY = {
    "vm_inventory_updater_fixed.py": "/home/banzo/vm_inventory_updater.py",
    "clover_creds.json": "/home/banzo/clover_creds.json",
    "service-account-key.json": "/home/banzo/service-account-key.json"
}

print("="*80)
print("CREATING FRESH VM IN DIFFERENT ZONE")
print("="*80)
print(f"\nNew VM Name: {VM_NAME}")
print(f"Zone: {ZONE} (different from us-central1)")
print(f"Project: {PROJECT_ID}")
print("\nThis will create a new VM with everything configured correctly\n")

# Read files
print("[1/4] Reading files...")
files_content = {}
for local_file, remote_path in FILES_TO_DEPLOY.items():
    if not os.path.exists(local_file):
        print(f"ERROR: {local_file} not found!")
        sys.exit(1)
    with open(local_file, 'r', encoding='utf-8') as f:
        files_content[remote_path] = f.read()
    print(f"  OK: {local_file} ({len(files_content[remote_path]):,} bytes)")

if "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4" in files_content["/home/banzo/vm_inventory_updater.py"]:
    print("  OK: February sheet ID verified")

# Build startup script
print("\n[2/4] Building startup script...")
startup_script = """#!/bin/bash
set -e
exec > /var/log/startup.log 2>&1
echo "=== Startup Script Started ==="
date

# Update system
apt-get update -y
apt-get install -y python3 python3-pip git

# Create user if doesn't exist
if ! id -u banzo &>/dev/null; then
    useradd -m -s /bin/bash banzo
fi

# Create directory
mkdir -p /home/banzo
chown -R banzo:banzo /home/banzo

# Install Python packages
pip3 install --upgrade pip
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests python-dotenv fuzzywuzzy python-Levenshtein

# Switch to banzo user and deploy files
su - banzo << 'DEPLOYFILES'
cd /home/banzo
"""

# Add file deployment (base64 encoded)
for remote_path, content in files_content.items():
    filename = os.path.basename(remote_path)
    content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    startup_script += f"""
# Deploy {filename}
echo '{content_b64}' | base64 -d > {remote_path}
chmod 644 {remote_path}
"""

startup_script += """
chmod +x /home/banzo/vm_inventory_updater.py

# Set up cron job
(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/banzo && /usr/bin/python3 /home/banzo/vm_inventory_updater.py >> /home/banzo/inventory_cron.log 2>&1") | crontab -

echo "=== Deployment Complete ==="
date
echo "Cron job configured:"
crontab -l
DEPLOYFILES

echo "=== Startup Script Finished ==="
date
"""

print(f"  OK: Startup script built ({len(startup_script):,} bytes)")

# Authenticate
print("\n[3/4] Authenticating...")
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

# Check if VM already exists
print("\n[4/4] Creating VM...")
try:
    existing = compute.instances().get(
        project=PROJECT_ID,
        zone=ZONE,
        instance=VM_NAME
    ).execute()
    print(f"  WARNING: VM '{VM_NAME}' already exists!")
    print(f"  Status: {existing.get('status')}")
    response = input("  Delete and recreate? (yes/no): ")
    if response.lower() == 'yes':
        print("  Deleting existing VM...")
        compute.instances().delete(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        print("  Waiting for deletion...")
        time.sleep(20)
    else:
        print("  Using existing VM")
        sys.exit(0)
except Exception as e:
    if "not found" not in str(e).lower():
        print(f"  ERROR checking VM: {e}")
        sys.exit(1)
    print("  VM doesn't exist, will create new one")

# VM configuration
machine_type = f"zones/{ZONE}/machineTypes/e2-micro"

config = {
    'name': VM_NAME,
    'machineType': machine_type,
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
    'metadata': {
        'items': [{
            'key': 'startup-script',
            'value': startup_script
        }]
    },
    'tags': {
        'items': ['inventory-updater']
    }
}

# Create VM with retry logic
max_retries = 5
operation = None

for attempt in range(max_retries):
    try:
        if attempt > 0:
            wait_time = attempt * 10
            print(f"  Retry {attempt + 1}/{max_retries} (waiting {wait_time}s)...")
            time.sleep(wait_time)
        else:
            print(f"  Creating VM...")
        
        operation = compute.instances().insert(
            project=PROJECT_ID,
            zone=ZONE,
            body=config
        ).execute()
        print("  OK: VM creation initiated!")
        break
    except Exception as e:
        error_str = str(e)
        if attempt < max_retries - 1 and ("503" in error_str or "unavailable" in error_str.lower()):
            continue  # Retry
        else:
            print(f"  ERROR: {e}")
            raise

if operation:
    print("\n" + "="*80)
    print("SUCCESS!")
    print("="*80)
    print(f"\nNew VM creation initiated!")
    print(f"VM Name: {VM_NAME}")
    print(f"Zone: {ZONE}")
    print(f"Operation ID: {operation['name']}")
    print(f"\nThe VM will be created in 2-5 minutes.")
    print(f"The startup script will automatically:")
    print(f"  - Install dependencies")
    print(f"  - Deploy all files")
    print(f"  - Set up cron job (runs every 5 minutes)")
    print(f"\nCheck status:")
    print(f"  python check_vm_creation_status.py")
    print(f"\nOr in Console:")
    print(f"  https://console.cloud.google.com/compute/instances?project={PROJECT_ID}")
else:
    print("\nERROR: Failed to create VM after retries")
    sys.exit(1)
