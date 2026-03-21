#!/usr/bin/env python3
"""
Quick fix: Copy deploy-and-setup to startup-script
"""

import os
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

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

def fix_startup_script():
    """Copy deploy-and-setup to startup-script"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/compute']
        )
        
        http = httplib2.Http(proxy_info=None, timeout=30)
        authorized_http = AuthorizedHttp(credentials, http=http)
        compute = build('compute', 'v1', http=authorized_http)
        
        # Get VM
        print("Getting VM metadata...")
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        metadata = instance.get('metadata', {})
        fingerprint = metadata.get('fingerprint', '')
        items = metadata.get('items', [])
        
        # Find deploy-and-setup script
        deploy_script = None
        for item in items:
            if item.get('key') == 'deploy-and-setup':
                deploy_script = item.get('value', '')
                break
        
        if not deploy_script:
            print("❌ deploy-and-setup not found")
            return False
        
        print(f"✅ Found deploy script ({len(deploy_script):,} bytes)")
        
        # Remove old startup-script, add new one
        items = [item for item in items if item.get('key') != 'startup-script']
        items.append({
            'key': 'startup-script',
            'value': deploy_script
        })
        
        # Update metadata
        print("Setting startup-script...")
        compute.instances().setMetadata(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME,
            body={
                'fingerprint': fingerprint,
                'items': items
            }
        ).execute()
        
        print("✅ startup-script set!")
        print("\nThe script will run on next VM restart.")
        print(f"Restart: gcloud compute instances reset {VM_NAME} --zone={ZONE} --project={PROJECT_ID}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if '503' in str(e):
            print("\n⚠️  API 503 error - this is a Google Cloud backend issue")
            print("This VM-specific problem prevents API calls from working.")
        return False

if __name__ == "__main__":
    fix_startup_script()
