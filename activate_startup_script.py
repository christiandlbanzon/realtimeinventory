#!/usr/bin/env python3
"""
Activate deployment by setting it as startup-script and restarting VM
"""

import os
import sys
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

# Essential files to deploy
FILES_TO_DEPLOY = {
    "vm_inventory_updater_fixed.py": "/home/banzo/vm_inventory_updater.py",
    "clover_creds.json": "/home/banzo/clover_creds.json",
    "service-account-key.json": "/home/banzo/service-account-key.json"
}

def activate_deployment():
    """Set deployment script as startup-script and restart VM"""
    print("="*80)
    print("ACTIVATING DEPLOYMENT (startup-script)")
    print("="*80)
    
    # Read files
    files_content = {}
    for local_file, remote_path in FILES_TO_DEPLOY.items():
        if not os.path.exists(local_file):
            print(f"❌ File not found: {local_file}")
            return False
        
        with open(local_file, 'r', encoding='utf-8') as f:
            content = f.read()
            files_content[remote_path] = content
            print(f"✅ Read {local_file} ({len(content):,} bytes)")
    
    # Create startup script (per Google Cloud docs)
    startup_script = f"""#!/bin/bash
set -e
cd /home/{VM_USER}

echo "=========================================="
echo "DEPLOYMENT STARTED"
echo "=========================================="

# Clean up old backups
rm -f /home/{VM_USER}/*.py.backup* 2>/dev/null || true

# Deploy files
echo "Deploying files..."
"""
    
    import base64
    for remote_path, content in files_content.items():
        filename = os.path.basename(remote_path)
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        startup_script += f"""
echo '{content_b64}' | base64 -d > {remote_path}
chmod 644 {remote_path}
echo "  ✅ {filename}"
"""
    
    startup_script += f"""
chmod +x /home/{VM_USER}/vm_inventory_updater.py

# Set up cron
echo ""
echo "Setting up cron job..."
(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/{VM_USER} && /usr/bin/python3 /home/{VM_USER}/vm_inventory_updater.py >> /home/{VM_USER}/inventory_cron.log 2>&1") | crontab -

echo ""
echo "=========================================="
echo "DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "Files deployed:"
ls -lh /home/{VM_USER}/*.py /home/{VM_USER}/*.json 2>/dev/null | grep -v ".backup" || true
echo ""
echo "Cron jobs:"
crontab -l
echo ""
echo "✅ VM is ready!"
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
        print(f"\n❌ Auth failed: {e}")
        return False
    
    try:
        # Get VM and current metadata
        print(f"\n[1/3] Getting VM metadata...")
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        status = instance.get('status', 'UNKNOWN')
        print(f"   VM Status: {status}")
        
        metadata = instance.get('metadata', {})
        fingerprint = metadata.get('fingerprint', '')
        items = metadata.get('items', [])
        
        # Remove old startup-script and deploy-and-setup, keep other items
        items = [item for item in items if item.get('key') not in ['startup-script', 'deploy-and-setup']]
        
        # Add new startup-script
        items.append({
            'key': 'startup-script',
            'value': startup_script
        })
        
        print(f"   Script size: {len(startup_script):,} bytes")
        
        # Set metadata with retries
        print(f"\n[2/3] Setting startup-script metadata...")
        max_retries = 3
        for attempt in range(max_retries):
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
                
                print("   ✅ Startup script set!")
                break
                
            except Exception as e:
                error_msg = str(e)
                if "503" in error_msg and attempt < max_retries - 1:
                    wait = (attempt + 1) * 3
                    print(f"   ⚠️  503 error (attempt {attempt + 1}/{max_retries}), waiting {wait}s...")
                    time.sleep(wait)
                    # Refresh fingerprint
                    instance = compute.instances().get(
                        project=PROJECT_ID,
                        zone=ZONE,
                        instance=VM_NAME
                    ).execute()
                    fingerprint = instance.get('metadata', {}).get('fingerprint', '')
                else:
                    print(f"   ❌ Error: {e}")
                    if "503" not in error_msg:
                        raise
        else:
            print("   ❌ Failed after retries")
            return False
        
        # Restart VM
        print(f"\n[3/3] Restarting VM to trigger startup script...")
        
        try:
            compute.instances().reset(
                project=PROJECT_ID,
                zone=ZONE,
                instance=VM_NAME
            ).execute()
            
            print("   ✅ VM restart initiated")
            print("\n⏳ VM is restarting...")
            print("   The startup script will run automatically during boot.")
            print("   This may take 1-2 minutes.")
            
            # Wait for restart
            print("\n   Waiting for VM to restart...")
            for i in range(60):
                time.sleep(2)
                try:
                    instance = compute.instances().get(
                        project=PROJECT_ID,
                        zone=ZONE,
                        instance=VM_NAME
                    ).execute()
                    
                    current_status = instance.get('status', 'UNKNOWN')
                    if current_status == 'RUNNING':
                        print(f"   ✅ VM is running (waited {i*2}s)")
                        print("\n✅ Deployment should have executed during startup!")
                        print("\nTo verify deployment, SSH and check:")
                        print(f"   gcloud compute ssh {VM_NAME} --zone={ZONE} --project={PROJECT_ID}")
                        print("   ls -lh /home/banzo/")
                        print("   crontab -l")
                        return True
                    elif i % 10 == 0:
                        print(f"   ⏳ Status: {current_status} (waited {i*2}s)")
                except:
                    pass
            
            print("   ⚠️  VM may still be restarting")
            print("   Check status manually or wait a bit longer")
            return True
            
        except Exception as e:
            error_msg = str(e)
            if "503" in error_msg:
                print(f"   ⚠️  503 error restarting VM: {e}")
                print("   But startup-script is set - it will run on next boot")
                print(f"   You can manually restart: gcloud compute instances reset {VM_NAME} --zone={ZONE}")
                return True
            else:
                raise
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = activate_deployment()
        if success:
            print("\n" + "="*80)
            print("✅ DEPLOYMENT ACTIVATED")
            print("="*80)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
