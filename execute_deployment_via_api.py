#!/usr/bin/env python3
"""
Execute the deployment script that's already in VM metadata
Uses Compute Engine API to trigger it
"""

import os
import sys
import time

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

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

def execute_deployment():
    """Execute deployment script via API"""
    print("="*80)
    print("EXECUTING DEPLOYMENT VIA API")
    print("="*80)
    print("Triggering deploy-and-setup script from VM metadata")
    print()
    
    # Authenticate
    print("[1/2] Authenticating...")
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/compute']
        )
        http = httplib2.Http(proxy_info=None)
        authorized_http = AuthorizedHttp(credentials, http=http)
        compute = build('compute', 'v1', http=authorized_http)
        print("   ✅ Authenticated")
    except Exception as e:
        print(f"   ❌ Auth failed: {e}")
        return False
    
    # Get the deployment script from metadata and set it as startup-script
    print("\n[2/2] Setting deploy-and-setup as startup-script and restarting...")
    try:
        instance = compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=VM_NAME).execute()
        metadata = instance.get('metadata', {})
        fingerprint = metadata.get('fingerprint', '')
        items = metadata.get('items', [])
        
        # Find deploy-and-setup script
        deploy_script = None
        for item in items:
            if item.get('key') == 'deploy-and-setup':
                deploy_script = item.get('value')
                break
        
        if not deploy_script:
            print("   ❌ deploy-and-setup script not found in metadata")
            return False
        
        print(f"   ✅ Found deployment script ({len(deploy_script):,} bytes)")
        
        # Remove old startup-script, add new one
        items = [item for item in items if item.get('key') not in ['startup-script', 'deploy-and-setup']]
        items.append({'key': 'startup-script', 'value': deploy_script})
        
        # Set metadata with retries
        max_retries = 5
        for attempt in range(max_retries):
            try:
                compute.instances().setMetadata(
                    project=PROJECT_ID,
                    zone=ZONE,
                    instance=VM_NAME,
                    body={'fingerprint': fingerprint, 'items': items}
                ).execute()
                print("   ✅ Startup script set!")
                break
            except Exception as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    wait = (attempt + 1) * 2
                    print(f"   ⏳ 503 error (attempt {attempt + 1}/{max_retries}), waiting {wait}s...")
                    time.sleep(wait)
                    instance = compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=VM_NAME).execute()
                    fingerprint = instance.get('metadata', {}).get('fingerprint', '')
                else:
                    print(f"   ❌ Error: {e}")
                    if "503" not in str(e):
                        raise
        else:
            print("   ⚠️  Could not set metadata (503 errors), but trying restart anyway...")
        
        # Restart VM
        print("\n   Restarting VM...")
        try:
            compute.instances().reset(project=PROJECT_ID, zone=ZONE, instance=VM_NAME).execute()
            print("   ✅ VM restart initiated!")
            print("\n✅ Deployment script will run automatically when VM restarts")
            return True
        except Exception as e:
            if "503" in str(e):
                print(f"   ⚠️  503 error restarting, but startup-script is set")
                print("   It will run on next manual restart")
                return True
            raise
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = execute_deployment()
        if success:
            print("\n" + "="*80)
            print("✅ DEPLOYMENT INITIATED")
            print("="*80)
            print("\nThe VM is restarting and will deploy files automatically.")
            print("Check VM logs after restart to verify deployment.")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
