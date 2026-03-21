#!/usr/bin/env python3
"""
Deploy files to VM using Compute Engine API - set startup-script
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
import time

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

def create_startup_script():
    """Create startup script that deploys files"""
    print("📦 Reading files to deploy...")
    files_content = {}
    
    for local_file, remote_path in FILES_TO_DEPLOY.items():
        if not os.path.exists(local_file):
            print(f"❌ File not found: {local_file}")
            return None
        
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
echo "✅ Script completed successfully"
"""
    
    return deploy_script

def set_startup_script(script_content):
    """Set startup-script metadata on VM"""
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
        
        # Get current metadata
        print(f"\n[1/3] Getting VM metadata...")
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        metadata = instance.get('metadata', {})
        fingerprint = metadata.get('fingerprint', '')
        items = metadata.get('items', [])
        
        # Remove existing startup-script if any
        items = [item for item in items if item.get('key') != 'startup-script']
        
        # Add startup-script
        items.append({
            'key': 'startup-script',
            'value': script_content
        })
        
        # Update metadata with retry logic
        print(f"[2/3] Setting startup-script metadata ({len(script_content):,} bytes)...")
        
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
                
                print("   ✅ startup-script set successfully!")
                return True
                
            except Exception as e:
                error_str = str(e)
                if '503' in error_str or 'unavailable' in error_str.lower():
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 3
                        print(f"   ⚠️  API error (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        # Refresh fingerprint
                        instance = compute.instances().get(
                            project=PROJECT_ID,
                            zone=ZONE,
                            instance=VM_NAME
                        ).execute()
                        fingerprint = instance.get('metadata', {}).get('fingerprint', '')
                        continue
                    else:
                        print(f"   ❌ Failed after {max_retries} attempts")
                        print(f"   Error: {e}")
                        return False
                else:
                    print(f"   ❌ Error: {e}")
                    return False
        
        return False
        
    except Exception as e:
        print(f"❌ Error setting startup-script: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*80)
    print("DEPLOYING TO VM VIA API")
    print("="*80)
    print(f"\nVM: {VM_NAME}")
    print(f"Zone: {ZONE}")
    
    # Create startup script
    script_content = create_startup_script()
    if not script_content:
        return False
    
    # Set startup-script
    success = set_startup_script(script_content)
    
    if success:
        print(f"\n[3/3] Deployment configured!")
        print("\n" + "="*80)
        print("✅ DEPLOYMENT READY")
        print("="*80)
        print("\nThe startup-script is now set. To deploy:")
        print(f"  1. Restart VM: gcloud compute instances reset {VM_NAME} --zone={ZONE} --project={PROJECT_ID}")
        print(f"  2. OR SSH and run manually: gcloud compute ssh {VM_NAME} --zone={ZONE} --project={PROJECT_ID}")
        print("     Then: curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/startup-script | bash")
    else:
        print("\n" + "="*80)
        print("⚠️  API SET FAILED")
        print("="*80)
        print("\nThe API call failed. This is a VM-specific issue.")
        print("Your other VMs work because they likely have startup-script already set.")
        print("\nTry running gcloud commands manually in your terminal:")
        print(f"  gcloud compute scp vm_inventory_updater_fixed.py banzo@{VM_NAME}:/home/banzo/vm_inventory_updater.py --zone={ZONE} --project={PROJECT_ID}")
    
    return success

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
