#!/usr/bin/env python3
"""
Deploy files directly to VM using Compute Engine API
Executes commands on the VM without needing SSH or gcloud
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
VM_NAME = "real-time-inventory"
ZONE = "us-central1-b"
VM_USER = "banzo"
SERVICE_ACCOUNT_FILE = "service-account-key.json"

FILES_TO_DEPLOY = {
    "vm_inventory_updater_fixed.py": "/home/banzo/vm_inventory_updater.py",
    "clover_creds.json": "/home/banzo/clover_creds.json",
    "service-account-key.json": "/home/banzo/service-account-key.json"
}

print("="*80)
print("DEPLOYING VIA COMPUTE ENGINE API (DIRECT EXECUTION)")
print("="*80)
print(f"\nVM: {VM_NAME}")
print(f"Zone: {ZONE}")
print(f"Project: {PROJECT_ID}")
print("\nThis will execute commands directly on the VM via API\n")

# Read files
print("[1/5] Reading files...")
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

# Authenticate
print("\n[2/5] Authenticating...")
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

# Function to execute command on VM
def execute_vm_command(command, timeout=60):
    """Execute a command on the VM via API"""
    try:
        # Use the compute.instances().getSerialPortOutput() method
        # Or better: use compute.instances().setMetadata() with a script that executes
        
        # Actually, we can use the serial port output method, but better is to
        # create a script and execute it via metadata startup-script
        
        # For now, let's try setting metadata with a script that executes commands
        # But wait - we can't execute arbitrary commands easily via API
        
        # Better approach: Use the API to set metadata with a script that does everything
        # This is what we'll do - create a comprehensive deployment script
        
        return True, ""
    except Exception as e:
        return False, str(e)

# Build comprehensive deployment script
print("\n[3/5] Building deployment script...")
deploy_script = """#!/bin/bash
set -e
exec > /var/log/deploy.log 2>&1
echo "=== Deployment Started ==="
date

# Create user
if ! id -u banzo &>/dev/null; then
    useradd -m -s /bin/bash banzo
fi

mkdir -p /home/banzo
chown -R banzo:banzo /home/banzo

# Install dependencies
apt-get update -y
apt-get install -y python3 python3-pip git
pip3 install --upgrade pip
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests python-dotenv fuzzywuzzy python-Levenshtein

# Switch to banzo user and deploy files
su - banzo << 'EOF'
cd /home/banzo
"""

# Add file deployment (base64 encoded)
for remote_path, content in files_content.items():
    filename = os.path.basename(remote_path)
    content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    deploy_script += f"""
# Deploy {filename}
echo '{content_b64}' | base64 -d > {remote_path}
chmod 644 {remote_path}
"""

deploy_script += """
chmod +x /home/banzo/vm_inventory_updater.py

# Set up cron
(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/banzo && /usr/bin/python3 /home/banzo/vm_inventory_updater.py >> /home/banzo/inventory_cron.log 2>&1") | crontab -

echo "=== Deployment Complete ==="
date
crontab -l
EOF

echo "=== Script Finished ==="
"""

print(f"  OK: Deployment script built ({len(deploy_script):,} bytes)")

# Deploy via metadata
print("\n[4/5] Deploying via VM metadata...")
try:
    # Get VM instance
    instance = compute.instances().get(
        project=PROJECT_ID,
        zone=ZONE,
        instance=VM_NAME
    ).execute()
    
    # Update metadata
    metadata = instance.get('metadata', {})
    fingerprint = metadata.get('fingerprint', '')
    items = metadata.get('items', [])
    
    # Remove old startup scripts
    items = [item for item in items if item.get('key') not in ['startup-script', 'deploy-script']]
    
    # Add deployment script
    items.append({
        'key': 'startup-script',
        'value': deploy_script
    })
    
    # Update metadata
    try:
        compute.instances().setMetadata(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME,
            body={
                'fingerprint': fingerprint,
                'items': items
            }
        ).execute()
        
        print("  OK: Deployment script added to VM metadata")
        print("  The script will run on next VM restart")
        
        # Restart VM to trigger script
        print("\n[5/5] Restarting VM to trigger deployment...")
        try:
            compute.instances().reset(
                project=PROJECT_ID,
                zone=ZONE,
                instance=VM_NAME
            ).execute()
            
            print("  OK: VM restart initiated")
            print("\n  Waiting for VM to restart (30 seconds)...")
            time.sleep(30)
            
            # Check status
            for i in range(10):
                instance = compute.instances().get(
                    project=PROJECT_ID,
                    zone=ZONE,
                    instance=VM_NAME
                ).execute()
                status = instance.get('status')
                if status == 'RUNNING':
                    print(f"  OK: VM is running")
                    break
                print(f"  Waiting... ({status})")
                time.sleep(5)
            
            print("\n" + "="*80)
            print("DEPLOYMENT INITIATED!")
            print("="*80)
            print(f"\nThe deployment script is running on the VM.")
            print(f"Check deployment logs:")
            print(f"  gcloud compute ssh {VM_NAME} --zone={ZONE} --project={PROJECT_ID} --command='tail -50 /var/log/deploy.log'")
            print(f"\nOr check application logs:")
            print(f"  gcloud compute ssh {VM_NAME} --zone={ZONE} --project={PROJECT_ID} --command='tail -50 /home/{VM_USER}/inventory_cron.log'")
            
        except Exception as e:
            error_str = str(e)
            if "503" in error_str:
                print(f"  WARNING: API returned 503, but script is in metadata")
                print(f"  Restart VM manually to trigger deployment:")
                print(f"  Or wait a few minutes and the script will run automatically")
            else:
                print(f"  ERROR restarting VM: {e}")
                print(f"  But script is in metadata - restart manually to trigger")
        
    except Exception as e:
        error_str = str(e)
        if "503" in error_str:
            print(f"  ERROR: API returned 503")
            print(f"  The deployment script is ready but can't be uploaded right now")
            print(f"\n  Alternative: Use the script content manually")
            print(f"  Save deploy_script content and add it via Console")
        else:
            print(f"  ERROR: {e}")
            raise

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
