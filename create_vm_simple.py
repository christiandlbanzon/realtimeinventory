#!/usr/bin/env python3
"""Create VM with simplified approach - no long waits"""

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

# Files to deploy
FILES_TO_DEPLOY = {
    "vm_inventory_updater_fixed.py": "/home/banzo/vm_inventory_updater.py",
    "clover_creds.json": "/home/banzo/clover_creds.json",
    "service-account-key.json": "/home/banzo/service-account-key.json"
}

def main():
    print("="*80)
    print("CREATING VM: real-time-inventory")
    print("="*80)
    
    # Verify files exist
    print("\n[0/4] Verifying files...")
    files_content = {}
    for local_file, remote_path in FILES_TO_DEPLOY.items():
        if not os.path.exists(local_file):
            print(f"   ERROR: {local_file} not found!")
            return False
        with open(local_file, 'r', encoding='utf-8') as f:
            content = f.read()
            files_content[remote_path] = content
        print(f"   OK: {local_file} ({len(content):,} bytes)")
    
    # Verify February sheet ID
    if "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4" in files_content["/home/banzo/vm_inventory_updater.py"]:
        print("   OK: February sheet ID found in code")
    else:
        print("   WARNING: February sheet ID not found!")
    
    # Authenticate
    print("\n[1/4] Authenticating...")
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
        print("   OK: Authenticated")
    except Exception as e:
        print(f"   ERROR: Authentication failed: {e}")
        return False
    
    # Check if VM exists
    print("\n[2/4] Checking if VM exists...")
    try:
        existing = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        print(f"   VM exists with status: {existing.get('status')}")
        print("   Deleting existing VM...")
        compute.instances().delete(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        print("   Waiting for deletion (30 seconds)...")
        time.sleep(30)
    except Exception as e:
        if "not found" in str(e).lower():
            print("   VM doesn't exist, will create new one")
        else:
            print(f"   Error checking VM: {e}")
            return False
    
    # Build startup script
    print("\n[3/4] Building startup script...")
    startup_script = f"""#!/bin/bash
set -e
exec > /var/log/startup.log 2>&1

echo "=== VM Startup Script ==="
date

# Update system
echo "Updating system..."
apt-get update -y
apt-get install -y python3 python3-pip git

# Create user if doesn't exist
if ! id -u {VM_USER} &>/dev/null; then
    useradd -m -s /bin/bash {VM_USER}
fi

# Create directory
mkdir -p /home/{VM_USER}
chown -R {VM_USER}:{VM_USER} /home/{VM_USER}

# Install Python packages
echo "Installing Python packages..."
pip3 install --upgrade pip
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests python-dotenv fuzzywuzzy python-Levenshtein

# Deploy files
echo "Deploying files..."
cd /home/{VM_USER}
"""
    
    for remote_path, content in files_content.items():
        filename = os.path.basename(remote_path)
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        startup_script += f"""
# Deploy {filename}
echo '{content_b64}' | base64 -d > {remote_path}
chmod 644 {remote_path}
"""
    
    startup_script += f"""
chmod +x /home/{VM_USER}/vm_inventory_updater.py

# Set up cron job
echo "Setting up cron job..."
(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/{VM_USER} && /usr/bin/python3 /home/{VM_USER}/vm_inventory_updater.py >> /home/{VM_USER}/inventory_cron.log 2>&1") | crontab -

echo "=== Deployment complete ==="
date
"""
    
    print(f"   OK: Startup script built ({len(startup_script):,} bytes)")
    
    # Create VM
    print("\n[4/4] Creating VM...")
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
            'accessConfigs': [{
                'type': 'ONE_TO_ONE_NAT',
                'name': 'External NAT'
            }]
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
    
    try:
        # Retry logic
        max_retries = 3
        operation = None
        for attempt in range(max_retries):
            try:
                operation = compute.instances().insert(
                    project=PROJECT_ID,
                    zone=ZONE,
                    body=config
                ).execute()
                break
            except Exception as e:
                if attempt < max_retries - 1 and ("503" in str(e) or "unavailable" in str(e).lower()):
                    wait_time = (attempt + 1) * 10
                    print(f"   API unavailable, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    raise
        
        if operation:
            print(f"   OK: VM creation initiated")
            print(f"   Operation: {operation['name']}")
            print("\n" + "="*80)
            print("VM CREATION STARTED")
            print("="*80)
            print(f"\nVM Name: {VM_NAME}")
            print(f"Zone: {ZONE}")
            print(f"\nThe VM is being created. This may take 2-5 minutes.")
            print(f"The startup script will automatically:")
            print(f"  - Install dependencies")
            print(f"  - Deploy all files")
            print(f"  - Set up cron job (runs every 5 minutes)")
            print(f"\nCheck status with: python check_vm_creation_status.py")
            print(f"Or in Google Cloud Console")
            return True
        else:
            print("   ERROR: Failed to create VM after retries")
            return False
            
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
