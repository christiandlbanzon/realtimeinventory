#!/usr/bin/env python3
"""
CLEAN VM CREATION - Simple, no-frills approach
If this fails, use manual Console creation (recommended)
"""

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
ZONE = "us-east1-b"
VM_NAME = "real-time-inventory"
SERVICE_ACCOUNT_FILE = "service-account-key.json"

FILES_TO_DEPLOY = {
    "vm_inventory_updater_fixed.py": "/home/banzo/vm_inventory_updater.py",
    "clover_creds.json": "/home/banzo/clover_creds.json",
    "service-account-key.json": "/home/banzo/service-account-key.json"
}

print("="*80)
print("CLEAN VM CREATION")
print("="*80)
print(f"\nVM: {VM_NAME}")
print(f"Zone: {ZONE}")
print(f"Project: {PROJECT_ID}\n")

# Read files
print("Reading files...")
files_content = {}
for local_file, remote_path in FILES_TO_DEPLOY.items():
    if not os.path.exists(local_file):
        print(f"ERROR: {local_file} not found!")
        sys.exit(1)
    with open(local_file, 'r', encoding='utf-8') as f:
        files_content[remote_path] = f.read()
    print(f"  OK: {local_file}")

# Build startup script
print("\nBuilding startup script...")
startup_script = """#!/bin/bash
set -e
exec > /var/log/startup.log 2>&1
echo "=== Startup Started ==="
date

apt-get update -y
apt-get install -y python3 python3-pip git

if ! id -u banzo &>/dev/null; then
    useradd -m -s /bin/bash banzo
fi

mkdir -p /home/banzo
chown -R banzo:banzo /home/banzo

pip3 install --upgrade pip
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests python-dotenv fuzzywuzzy python-Levenshtein

su - banzo << 'EOF'
cd /home/banzo
"""

for remote_path, content in files_content.items():
    content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    startup_script += f"echo '{content_b64}' | base64 -d > {remote_path}\n"
    startup_script += f"chmod 644 {remote_path}\n"

startup_script += """chmod +x /home/banzo/vm_inventory_updater.py
(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/banzo && /usr/bin/python3 /home/banzo/vm_inventory_updater.py >> /home/banzo/inventory_cron.log 2>&1") | crontab -
crontab -l
EOF
echo "=== Complete ==="
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
    http = httplib2.Http(proxy_info=None, timeout=30)
    authorized_http = AuthorizedHttp(credentials, http=http)
    compute = build('compute', 'v1', http=authorized_http)
    print("  OK: Authenticated")
except Exception as e:
    print(f"  ERROR: {e}")
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
    'metadata': {
        'items': [{'key': 'startup-script', 'value': startup_script}]
    },
    'tags': {'items': ['inventory-updater']}
}

# Create VM
print("\nCreating VM (this may take 30-60 seconds)...")
print("If this times out, use manual Console creation instead.")
print()

try:
    operation = compute.instances().insert(
        project=PROJECT_ID,
        zone=ZONE,
        body=config
    ).execute()
    
    print("="*80)
    print("SUCCESS!")
    print("="*80)
    print(f"\nVM creation initiated!")
    print(f"Operation: {operation['name']}")
    print(f"\nVM will be ready in 2-5 minutes")
    print(f"Startup script will configure everything automatically")
    print(f"\nCheck status:")
    print(f"  python check_all_vms.py")
    print(f"\nOr in Console:")
    print(f"  https://console.cloud.google.com/compute/instances?project={PROJECT_ID}")
    
except Exception as e:
    error_str = str(e)
    print("="*80)
    print("FAILED")
    print("="*80)
    print(f"\nError: {e}")
    
    if "503" in error_str or "timeout" in error_str.lower():
        print("\n" + "="*80)
        print("RECOMMENDATION: Use Manual Console Creation")
        print("="*80)
        print("\nThe Google Cloud API is timing out.")
        print("This is a Google Cloud service issue, not your code.")
        print("\nSOLUTION:")
        print("1. Go to: https://console.cloud.google.com/compute/instances/create?project=boxwood-chassis-332307")
        print("2. Name: real-time-inventory")
        print("3. Zone: us-east1-b")
        print("4. Machine type: e2-micro")
        print("5. Boot disk: Debian 12")
        print("6. Under 'Management' → 'Automation' → 'Startup script'")
        print("7. Paste the entire content from: startup_script.sh")
        print("8. Click 'Create'")
        print("\nThis will work because Console UI bypasses API issues.")
    
    sys.exit(1)
