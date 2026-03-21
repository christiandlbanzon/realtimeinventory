#!/usr/bin/env python3
"""Create VM with simple approach - catch and show errors clearly"""

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
VM_NAME = "real-time-inventory-v2"
SERVICE_ACCOUNT_FILE = "service-account-key.json"
VM_USER = "banzo"

FILES_TO_DEPLOY = {
    "vm_inventory_updater_fixed.py": "/home/banzo/vm_inventory_updater.py",
    "clover_creds.json": "/home/banzo/clover_creds.json",
    "service-account-key.json": "/home/banzo/service-account-key.json"
}

print("="*80)
print("CREATING FRESH VM")
print("="*80)
print(f"\nVM: {VM_NAME}")
print(f"Zone: {ZONE}")
print(f"Project: {PROJECT_ID}\n")

# Read files
files_content = {}
for local_file, remote_path in FILES_TO_DEPLOY.items():
    if not os.path.exists(local_file):
        print(f"ERROR: {local_file} not found!")
        sys.exit(1)
    with open(local_file, 'r', encoding='utf-8') as f:
        files_content[remote_path] = f.read()
    print(f"OK: {local_file}")

# Build startup script
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

print(f"OK: Startup script ({len(startup_script):,} bytes)")

# Authenticate
try:
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/compute']
    )
    http = httplib2.Http(proxy_info=None, timeout=30)
    authorized_http = AuthorizedHttp(credentials, http=http)
    compute = build('compute', 'v1', http=authorized_http)
    print("OK: Authenticated")
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
    'metadata': {
        'items': [{'key': 'startup-script', 'value': startup_script}]
    },
    'tags': {'items': ['inventory-updater']}
}

# Create VM
print("\nCreating VM...")
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
    print(f"\nCheck: python check_all_vms.py")
    
except Exception as e:
    error_str = str(e)
    print(f"\nERROR: {e}")
    
    if "503" in error_str:
        print("\nGoogle Cloud API is still returning 503 errors")
        print("This is a Google Cloud service issue, not your code")
        print("\nOptions:")
        print("1. Wait 30-60 minutes and try again")
        print("2. Create VM manually via Console:")
        print(f"   https://console.cloud.google.com/compute/instances/create?project={PROJECT_ID}")
        print("3. Use the startup script content from startup_script.sh")
    elif "quota" in error_str.lower():
        print("\nQuota issue detected")
        print("You may have reached your VM quota limit")
    elif "permission" in error_str.lower():
        print("\nPermission issue detected")
        print("Service account may need additional permissions")
    else:
        import traceback
        traceback.print_exc()
    
    sys.exit(1)
