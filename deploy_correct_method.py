#!/usr/bin/env python3
"""
Deploy using correct method per Google Cloud documentation
Uses startup-script metadata key which runs automatically on boot
"""

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

def deploy_via_startup_script():
    """Deploy using startup-script (runs automatically on boot)"""
    print("="*80)
    print("DEPLOYING VIA STARTUP SCRIPT (CORRECT METHOD)")
    print("="*80)
    print(f"\nVM: {VM_NAME}")
    print(f"Using service account: {SERVICE_ACCOUNT_FILE}")
    
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

# Clean up
rm -f /home/{VM_USER}/*.py.backup* /home/{VM_USER}/*.log 2>/dev/null || true

# Deploy files
echo "Deploying files..."
"""
    
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
        
        print("\n✅ Authenticated with service account")
    except Exception as e:
        print(f"\n❌ Auth failed: {e}")
        return False
    
    # Get VM and update metadata
    try:
        print(f"\n[1/2] Getting VM and updating startup-script metadata...")
        
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
        
        # Remove old startup-script, keep other items
        items = [item for item in items if item.get('key') != 'startup-script']
        
        # Add new startup-script (per Google Cloud docs)
        items.append({
            'key': 'startup-script',
            'value': startup_script
        })
        
        # Retry for 503 errors
        max_retries = 5
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
                
                print("   ✅ Startup script set in metadata")
                break
                
            except Exception as e:
                error_msg = str(e)
                if "503" in error_msg and attempt < max_retries - 1:
                    wait = (attempt + 1) * 5
                    print(f"   ⚠️  503 error (attempt {attempt + 1}/{max_retries}), waiting {wait}s...")
                    time.sleep(wait)
                    # Refresh
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
            print("   ❌ Failed after retries - API still returning 503")
            return False
        
        # Restart VM to trigger startup script
        print(f"\n[2/2] Restarting VM to trigger startup script...")
        
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
            for i in range(60):
                time.sleep(2)
                instance = compute.instances().get(
                    project=PROJECT_ID,
                    zone=ZONE,
                    instance=VM_NAME
                ).execute()
                
                if instance.get('status') == 'RUNNING':
                    print("   ✅ VM is running")
                    print("\n✅ Deployment script should have executed during startup!")
                    return True
            
            print("   ⚠️  VM may still be restarting")
            return True
            
        except Exception as e:
            error_msg = str(e)
            if "503" in error_msg:
                print(f"   ⚠️  503 error restarting VM: {e}")
                print("   But startup-script is set - it will run on next boot")
                print("   You can manually restart: gcloud compute instances reset real-time-inventory --zone=us-central1-a")
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
        success = deploy_via_startup_script()
        if success:
            print("\n" + "="*80)
            print("✅ DEPLOYMENT INITIATED")
            print("="*80)
            print("\nThe startup script is set and VM is restarting.")
            print("Files will be deployed automatically during boot.")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
