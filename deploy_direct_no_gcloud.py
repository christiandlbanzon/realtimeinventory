#!/usr/bin/env python3
"""
Deploy directly using Compute Engine API - NO gcloud needed
Uses service account credentials only
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

def deploy_direct():
    """Deploy files directly using API - no gcloud needed"""
    print("="*80)
    print("DEPLOYING DIRECTLY VIA API (NO GCLOUD NEEDED)")
    print("="*80)
    print(f"\nUsing service account: {SERVICE_ACCOUNT_FILE}")
    print(f"VM: {VM_NAME}")
    
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

echo "🧹 Cleaning up..."
rm -f /home/{VM_USER}/*.py.backup* /home/{VM_USER}/*.log 2>/dev/null || true

echo "📦 Deploying files..."
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
chmod +x /home/{VM_USER}/vm_inventory_updater.py

echo ""
echo "⏰ Setting up cron..."
(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/{VM_USER} && /usr/bin/python3 /home/{VM_USER}/vm_inventory_updater.py >> /home/{VM_USER}/inventory_cron.log 2>&1") | crontab -

echo ""
echo "✅ Deployment complete!"
echo ""
ls -lh /home/{VM_USER}/*.py /home/{VM_USER}/*.json 2>/dev/null | grep -v ".backup" || true
echo ""
crontab -l
"""
    
    # Authenticate with service account
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
        
        print("\n✅ Authenticated with service account (NO gcloud auth needed)")
    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        return False
    
    # Get VM
    try:
        print(f"\n[1/3] Getting VM info...")
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        status = instance.get('status', 'UNKNOWN')
        print(f"✅ VM Status: {status}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    
    # Set metadata with retries for 503 errors
    try:
        print(f"\n[2/3] Setting deployment script in metadata (with retries for 503)...")
        
        metadata = instance.get('metadata', {})
        fingerprint = metadata.get('fingerprint', '')
        items = metadata.get('items', [])
        
        # Remove old scripts
        items = [item for item in items if item.get('key') not in ['startup-script', 'deploy-and-setup', 'deploy-script']]
        
        # Add deployment script as startup script
        items.append({
            'key': 'startup-script',
            'value': deploy_script
        })
        
        # Retry logic for 503 errors
        max_retries = 5
        success = False
        
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
                
                print("✅ Metadata updated successfully!")
                success = True
                break
                
            except Exception as e:
                error_msg = str(e)
                if "503" in error_msg and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    print(f"   ⚠️  503 error (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s...")
                    time.sleep(wait_time)
                    # Refresh instance and fingerprint
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
        
        if not success:
            print("\n❌ Could not update metadata after retries")
            print("   This is a temporary Google Cloud API issue")
            return False
        
    except Exception as e:
        print(f"\n❌ Error setting metadata: {e}")
        return False
    
    # Restart VM to trigger startup script
    try:
        print(f"\n[3/3] Restarting VM to execute deployment...")
        
        compute.instances().reset(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        print("✅ VM restart initiated")
        print("\n⏳ VM is restarting...")
        print("   Deployment script will run automatically on startup.")
        print("   Waiting for restart (this may take 1-2 minutes)...")
        
        # Wait for restart
        for i in range(60):
            time.sleep(2)
            try:
                instance = compute.instances().get(
                    project=PROJECT_ID,
                    zone=ZONE,
                    instance=VM_NAME
                ).execute()
                
                if instance.get('status') == 'RUNNING':
                    print("   ✅ VM is running")
                    print("\n✅ Deployment should have executed during startup!")
                    print("\nTo verify:")
                    print(f"   gcloud compute ssh {VM_NAME} --zone={ZONE} --project={PROJECT_ID} --command='ls -lh /home/banzo/ && crontab -l'")
                    return True
            except:
                pass
        
        print("   ⚠️  VM may still be restarting")
        print("   Deployment script is set - it will run on startup")
        return True
        
    except Exception as e:
        print(f"\n⚠️  Error restarting VM: {e}")
        print("   But startup script is set - it will run on next boot")
        return True

if __name__ == "__main__":
    try:
        success = deploy_direct()
        if success:
            print("\n" + "="*80)
            print("✅ DEPLOYMENT INITIATED")
            print("="*80)
            print("\nFiles are being deployed via startup script.")
            print("The VM will restart and deploy automatically.")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
