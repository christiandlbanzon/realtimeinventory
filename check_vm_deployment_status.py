#!/usr/bin/env python3
"""
Check VM deployment status - verify what's actually deployed
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

PROJECT_ID = "boxwood-chassis-332307"
ZONE = "us-central1-a"
VM_NAME = "real-time-inventory"
SERVICE_ACCOUNT_FILE = "service-account-key.json"

def check_vm_status():
    """Check VM status, metadata, and deployment state"""
    print("="*80)
    print("CHECKING VM DEPLOYMENT STATUS")
    print("="*80)
    
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
        
        print("✅ Authenticated\n")
    except Exception as e:
        print(f"❌ Auth failed: {e}")
        return False
    
    try:
        # Get VM instance
        print(f"[1/3] Getting VM instance: {VM_NAME}...")
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        # VM Status
        status = instance.get('status', 'UNKNOWN')
        print(f"   ✅ VM Status: {status}")
        
        # Network
        network_interfaces = instance.get('networkInterfaces', [])
        if network_interfaces:
            access_configs = network_interfaces[0].get('accessConfigs', [])
            if access_configs:
                external_ip = access_configs[0].get('natIP', 'N/A')
                print(f"   ✅ External IP: {external_ip}")
        
        # Metadata
        print(f"\n[2/3] Checking VM metadata...")
        metadata = instance.get('metadata', {})
        items = metadata.get('items', [])
        
        print(f"   Found {len(items)} metadata items:")
        
        deployment_scripts = []
        for item in items:
            key = item.get('key', '')
            value = item.get('value', '')
            value_preview = value[:100] + '...' if len(value) > 100 else value
            
            if key in ['startup-script', 'deploy-and-setup', 'deploy-clean']:
                deployment_scripts.append(key)
                print(f"   🔧 {key}: {len(value)} bytes")
                print(f"      Preview: {value_preview[:200]}...")
            else:
                print(f"   📝 {key}: {len(str(value))} chars")
        
        if not deployment_scripts:
            print("   ⚠️  No deployment scripts found in metadata")
        else:
            print(f"\n   ✅ Found deployment scripts: {', '.join(deployment_scripts)}")
        
        # Check what files should be deployed
        print(f"\n[3/3] Expected files on VM:")
        expected_files = [
            "/home/banzo/vm_inventory_updater.py",
            "/home/banzo/clover_creds.json",
            "/home/banzo/service-account-key.json"
        ]
        
        for file_path in expected_files:
            print(f"   📄 {file_path}")
        
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"VM Name: {VM_NAME}")
        print(f"Status: {status}")
        print(f"Deployment Scripts in Metadata: {len(deployment_scripts)}")
        
        if status == 'RUNNING':
            print("\n✅ VM is running")
            if deployment_scripts:
                print("✅ Deployment scripts are in metadata")
                print("\nTo execute deployment:")
                print("   Option 1: Restart VM (startup-script runs automatically)")
                print("   Option 2: SSH and run manually:")
                print(f"      gcloud compute ssh {VM_NAME} --zone={ZONE} --project={PROJECT_ID}")
                print("      Then check if files exist: ls -lh /home/banzo/")
            else:
                print("⚠️  No deployment scripts found - need to add startup-script")
        else:
            print(f"\n⚠️  VM is {status} - start it first")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        check_vm_status()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
