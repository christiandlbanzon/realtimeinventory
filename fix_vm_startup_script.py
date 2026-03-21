#!/usr/bin/env python3
"""
Fix VM by copying deploy-and-setup to startup-script OR use gcloud scp
"""

import os
import sys

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

def get_deploy_script_from_metadata():
    """Get deploy-and-setup script from VM metadata"""
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
        
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        metadata = instance.get('metadata', {})
        items = metadata.get('items', [])
        
        for item in items:
            if item.get('key') == 'deploy-and-setup':
                return item.get('value', '')
        
        return None
    except Exception as e:
        print(f"❌ Error getting metadata: {e}")
        return None

def set_startup_script(script_content):
    """Set startup-script metadata"""
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
        
        # Update metadata
        print(f"\n[2/2] Setting startup-script metadata...")
        print(f"   Script size: {len(script_content):,} bytes")
        
        # Retry logic for 503 errors
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
                
                print("   ✅ startup-script set successfully!")
                return True
                
            except Exception as e:
                if '503' in str(e) or 'unavailable' in str(e).lower():
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5
                        print(f"   ⚠️  API error (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"   ❌ Failed after {max_retries} attempts: {e}")
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
    print("FIXING VM: Setting startup-script from deploy-and-setup")
    print("="*80)
    print(f"\nVM: {VM_NAME}")
    print(f"Zone: {ZONE}")
    
    # Get deploy script from metadata
    print(f"\n[1/2] Getting deploy-and-setup script from VM metadata...")
    deploy_script = get_deploy_script_from_metadata()
    
    if not deploy_script:
        print("   ❌ deploy-and-setup script not found in metadata")
        print("\n   Alternative: Use gcloud scp to deploy files directly")
        print("   (This is what your other working VMs use)")
        print("\n   Commands:")
        print(f"   gcloud compute scp vm_inventory_updater_fixed.py banzo@{VM_NAME}:/home/banzo/vm_inventory_updater.py --zone={ZONE} --project={PROJECT_ID}")
        print(f"   gcloud compute scp clover_creds.json banzo@{VM_NAME}:/home/banzo/clover_creds.json --zone={ZONE} --project={PROJECT_ID}")
        print(f"   gcloud compute scp service-account-key.json banzo@{VM_NAME}:/home/banzo/service-account-key.json --zone={ZONE} --project={PROJECT_ID}")
        return False
    
    print(f"   ✅ Found deploy script ({len(deploy_script):,} bytes)")
    
    # Set as startup-script
    success = set_startup_script(deploy_script)
    
    if success:
        print("\n" + "="*80)
        print("✅ FIXED!")
        print("="*80)
        print("\nThe startup-script is now set. It will run:")
        print("  - On next VM boot/restart")
        print("  - OR you can restart now: gcloud compute instances reset " + VM_NAME + f" --zone={ZONE} --project={PROJECT_ID}")
        print("\nThis matches how your other working VMs are configured!")
    else:
        print("\n" + "="*80)
        print("⚠️  API SET FAILED - Use gcloud Instead")
        print("="*80)
        print("\nSince API calls are failing, use gcloud scp (like your other VMs):")
        print(f"\n   gcloud compute scp vm_inventory_updater_fixed.py banzo@{VM_NAME}:/home/banzo/vm_inventory_updater.py --zone={ZONE} --project={PROJECT_ID}")
        print(f"   gcloud compute scp clover_creds.json banzo@{VM_NAME}:/home/banzo/clover_creds.json --zone={ZONE} --project={PROJECT_ID}")
        print(f"   gcloud compute scp service-account-key.json banzo@{VM_NAME}:/home/banzo/service-account-key.json --zone={ZONE} --project={PROJECT_ID}")
        print(f"\n   gcloud compute ssh {VM_NAME} --zone={ZONE} --project={PROJECT_ID} --command=\"(crontab -l 2>/dev/null | grep -v 'vm_inventory_updater.py'; echo '*/5 * * * * cd /home/banzo && /usr/bin/python3 /home/banzo/vm_inventory_updater.py >> /home/banzo/inventory_cron.log 2>&1') | crontab -\"")
    
    return success

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
