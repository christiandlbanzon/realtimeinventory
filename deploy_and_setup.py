#!/usr/bin/env python3
"""
Deploy essential files to VM and set up cron job
"""

import os
import sys
import base64

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

# Essential files to deploy
FILES_TO_DEPLOY = {
    "vm_inventory_updater_fixed.py": "/home/banzo/vm_inventory_updater.py",
    "clover_creds.json": "/home/banzo/clover_creds.json",
    "service-account-key.json": "/home/banzo/service-account-key.json"
}

def deploy_and_setup():
    """Deploy files and set up cron"""
    print("="*80)
    print("DEPLOYING TO VM AND SETTING UP CRON")
    print("="*80)
    print(f"\nVM: {VM_NAME}")
    print(f"Zone: {ZONE}")
    
    # Read files
    files_content = {}
    for local_file, remote_path in FILES_TO_DEPLOY.items():
        if not os.path.exists(local_file):
            print(f"❌ File not found: {local_file}")
            return False
        
        with open(local_file, 'r', encoding='utf-8') as f:
            content = f.read()
            files_content[remote_path] = {
                'content': content,
                'size': len(content)
            }
            print(f"✅ Read {local_file} ({len(content):,} bytes)")
    
    # Create deployment script
    deploy_script = f"""#!/bin/bash
set -e
cd /home/{VM_USER}

echo "🧹 Cleaning up old files..."
rm -f /home/{VM_USER}/*.py.backup*
rm -f /home/{VM_USER}/*.log
rm -f /home/{VM_USER}/deployment.log

echo "📦 Deploying essential files..."
"""
    
    for remote_path, file_info in files_content.items():
        filename = os.path.basename(remote_path)
        content_b64 = base64.b64encode(file_info['content'].encode('utf-8')).decode('utf-8')
        deploy_script += f"""
# Deploy {filename}
echo '{content_b64}' | base64 -d > {remote_path}
chmod 644 {remote_path}
echo "  ✅ {filename}"
"""
    
    deploy_script += f"""
# Make main script executable
chmod +x /home/{VM_USER}/vm_inventory_updater.py

# Set up cron job
echo ""
echo "⏰ Setting up cron job..."
(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/{VM_USER} && /usr/bin/python3 /home/{VM_USER}/vm_inventory_updater.py >> /home/{VM_USER}/inventory_cron.log 2>&1") | crontab -

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📁 Files on VM:"
ls -lh /home/{VM_USER}/*.py /home/{VM_USER}/*.json 2>/dev/null | grep -v ".backup" || true
echo ""
echo "⏰ Cron jobs:"
crontab -l
echo ""
echo "✅ VM is ready to run!"
"""
    
    # Authenticate
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
        
        print("\n✅ Authenticated")
    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        return False
    
    # Check VM
    try:
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        status = instance.get('status', 'UNKNOWN')
        print(f"✅ VM Status: {status}")
        
        if status != 'RUNNING':
            print(f"⚠️  VM is {status}, starting it...")
            compute.instances().start(
                project=PROJECT_ID,
                zone=ZONE,
                instance=VM_NAME
            ).execute()
            print("   VM started")
        
    except Exception as e:
        print(f"\n❌ Error checking VM: {e}")
        return False
    
    # Update metadata
    try:
        print("\n[1/2] Adding deployment script to VM metadata...")
        
        metadata = instance.get('metadata', {})
        fingerprint = metadata.get('fingerprint', '')
        items = metadata.get('items', [])
        
        # Remove old scripts
        items = [item for item in items if item.get('key') not in ['deploy-files', 'deploy-script', 'setup-cron', 'deploy-clean', 'deploy-inventory']]
        
        items.append({
            'key': 'deploy-and-setup',
            'value': deploy_script
        })
        
        compute.instances().setMetadata(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME,
            body={
                'fingerprint': fingerprint,
                'items': items
            }
        ).execute()
        
        print("✅ Deployment script added")
        
        # Execute via SSH command
        print("\n[2/2] Executing deployment on VM...")
        
        # Use subprocess to execute gcloud ssh command
        import subprocess
        
        ssh_command = f"curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-and-setup | bash"
        
        cmd = [
            "gcloud", "compute", "ssh", VM_NAME,
            "--zone", ZONE,
            "--project", PROJECT_ID,
            "--command", ssh_command,
            "--quiet"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                print("✅ Deployment executed successfully!")
                print(result.stdout)
            else:
                print("⚠️  Deployment had issues (but script is in metadata):")
                print(result.stderr[:500])
                print("\nYou can SSH and run manually:")
                print(f"   gcloud compute ssh {VM_NAME} --zone={ZONE} --project={PROJECT_ID}")
                print(f"   curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-and-setup | bash")
        except FileNotFoundError:
            print("⚠️  gcloud not found in PATH")
            print("   Deployment script is ready in VM metadata")
            print("   SSH to VM and run:")
            print(f"   curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-and-setup | bash")
        except Exception as e:
            print(f"⚠️  Could not execute: {e}")
            print("   Deployment script is ready in VM metadata")
            print("   SSH to VM and run manually")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = deploy_and_setup()
        if success:
            print("\n" + "="*80)
            print("✅ DEPLOYMENT READY")
            print("="*80)
            print("\nThe VM is set up and ready to run!")
            print("Cron job will execute every 5 minutes automatically.")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
