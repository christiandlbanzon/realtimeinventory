#!/usr/bin/env python3
"""
Deploy files using ONLY the Compute Engine API (no SSH, no gcloud CLI)
Uses service account authentication - fully automated
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

FILES_TO_DEPLOY = {
    "vm_inventory_updater_fixed.py": "/home/banzo/vm_inventory_updater.py",
    "clover_creds.json": "/home/banzo/clover_creds.json",
    "service-account-key.json": "/home/banzo/service-account-key.json"
}

def deploy_via_api():
    """Deploy files using ONLY Compute Engine API - no SSH, no gcloud CLI"""
    print("="*80)
    print("DEPLOYING VIA COMPUTE ENGINE API ONLY")
    print("="*80)
    print("Using service account authentication - no SSH/gcloud needed")
    print(f"\nVM: {VM_NAME}")
    print(f"Zone: {ZONE}")
    
    # Read files
    files_content = {}
    for local_file, remote_path in FILES_TO_DEPLOY.items():
        if not os.path.exists(local_file):
            print(f"\n❌ File not found: {local_file}")
            return False
        
        with open(local_file, 'r', encoding='utf-8') as f:
            content = f.read()
            files_content[remote_path] = content
            print(f"✅ Read {local_file} ({len(content):,} bytes)")
    
    # Create startup script that will deploy files
    startup_script = f"""#!/bin/bash
set -e
cd /home/{VM_USER}

echo "=========================================="
echo "DEPLOYMENT VIA API - STARTED"
echo "=========================================="
echo "Timestamp: $(date)"
echo ""

# Clean up old backups
rm -f /home/{VM_USER}/*.py.backup* 2>/dev/null || true

# Deploy files from base64
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

# Set up cron job
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
    
    # Authenticate with service account
    print("\n[1/4] Authenticating with service account...")
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
        
        print("   ✅ Authenticated via service account")
    except Exception as e:
        print(f"   ❌ Auth failed: {e}")
        return False
    
    # Get VM instance
    print("\n[2/4] Getting VM instance...")
    try:
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        status = instance.get('status', 'UNKNOWN')
        print(f"   ✅ VM Status: {status}")
        
        if status != 'RUNNING':
            print(f"   ⚠️  VM is {status}, starting it...")
            compute.instances().start(
                project=PROJECT_ID,
                zone=ZONE,
                instance=VM_NAME
            ).execute()
            print("   ✅ VM started")
            
            # Wait for VM to be running
            for i in range(30):
                time.sleep(2)
                instance = compute.instances().get(
                    project=PROJECT_ID,
                    zone=ZONE,
                    instance=VM_NAME
                ).execute()
                if instance.get('status') == 'RUNNING':
                    break
        
        metadata = instance.get('metadata', {})
        fingerprint = metadata.get('fingerprint', '')
        items = metadata.get('items', [])
        
        print(f"   ✅ Got VM metadata (fingerprint: {fingerprint[:16]}...)")
        
    except Exception as e:
        print(f"   ❌ Error getting VM: {e}")
        return False
    
    # Set startup-script metadata
    print("\n[3/4] Setting startup-script metadata via API...")
    print(f"   Script size: {len(startup_script):,} bytes")
    
    # Remove old startup scripts
    items = [item for item in items if item.get('key') not in ['startup-script', 'deploy-and-setup']]
    
    # Add new startup-script
    items.append({
        'key': 'startup-script',
        'value': startup_script
    })
    
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
            
            print("   ✅ Startup script set via API!")
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
        print("   ❌ Failed after retries - Google Cloud API returning 503")
        print("   This is a temporary Google Cloud backend issue, not an auth problem")
        return False
    
    # Restart VM to trigger startup script
    print("\n[4/4] Restarting VM via API to trigger startup script...")
    
    try:
        compute.instances().reset(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        print("   ✅ VM restart initiated via API")
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
                    print("\nThe startup script deployed all files and set up cron automatically.")
                    return True
                elif i % 10 == 0:
                    print(f"   ⏳ Status: {current_status} (waited {i*2}s)")
            except:
                pass
        
        print("   ⚠️  VM may still be restarting")
        print("   Deployment will complete when VM finishes booting")
        return True
        
    except Exception as e:
        error_msg = str(e)
        if "503" in error_msg:
            print(f"   ⚠️  503 error restarting VM: {e}")
            print("   But startup-script is set - it will run on next boot")
            print("   This is a temporary Google Cloud backend issue")
            return True
        else:
            print(f"   ❌ Error: {e}")
            raise

if __name__ == "__main__":
    try:
        print("\n" + "="*80)
        print("USING COMPUTE ENGINE API ONLY")
        print("No SSH, no gcloud CLI - pure API calls")
        print("="*80)
        
        success = deploy_via_api()
        
        if success:
            print("\n" + "="*80)
            print("✅ DEPLOYMENT INITIATED VIA API")
            print("="*80)
            print("\nFiles will be deployed automatically when VM restarts.")
            print("Startup script is set and will run on boot.")
        else:
            print("\n" + "="*80)
            print("⚠️  DEPLOYMENT HAD ISSUES")
            print("="*80)
            print("\nGoogle Cloud API returned 503 errors (temporary backend issue).")
            print("The startup script may still be set - check VM metadata.")
        
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
