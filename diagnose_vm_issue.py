#!/usr/bin/env python3
"""
Diagnose VM-specific issues - compare with working VMs
"""

import os
import sys
import json

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
SERVICE_ACCOUNT_FILE = "service-account-key.json"

def get_vm_details(vm_name):
    """Get detailed VM configuration"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=[
                'https://www.googleapis.com/auth/cloud-platform',
                'https://www.googleapis.com/auth/compute.readonly'
            ]
        )
        
        http = httplib2.Http(proxy_info=None)
        authorized_http = AuthorizedHttp(credentials, http=http)
        compute = build('compute', 'v1', http=authorized_http)
        
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=vm_name
        ).execute()
        
        return instance
    except Exception as e:
        print(f"❌ Error getting VM {vm_name}: {e}")
        return None

def compare_vms():
    """Compare real-time-inventory with other VMs"""
    print("="*80)
    print("VM DIAGNOSIS - Comparing Configurations")
    print("="*80)
    
    vms_to_check = [
        "real-time-inventory",
        # Add your working VMs here if you know their names
        # "shopify-cookie-automation-vm",
        # "operations-part-1-vm"
    ]
    
    for vm_name in vms_to_check:
        print(f"\n{'='*80}")
        print(f"VM: {vm_name}")
        print(f"{'='*80}")
        
        instance = get_vm_details(vm_name)
        if not instance:
            continue
        
        # Status
        status = instance.get('status', 'UNKNOWN')
        print(f"Status: {status}")
        
        # Service Accounts
        service_accounts = instance.get('serviceAccounts', [])
        print(f"\nService Accounts ({len(service_accounts)}):")
        for sa in service_accounts:
            email = sa.get('email', 'N/A')
            scopes = sa.get('scopes', [])
            print(f"  - {email}")
            print(f"    Scopes: {len(scopes)} scopes")
        
        # Metadata
        metadata = instance.get('metadata', {})
        items = metadata.get('items', [])
        print(f"\nMetadata Items ({len(items)}):")
        
        has_startup_script = False
        has_deploy_script = False
        
        for item in items:
            key = item.get('key', '')
            value = item.get('value', '')
            
            if key == 'startup-script':
                has_startup_script = True
                print(f"  ✅ startup-script: {len(value)} bytes")
            elif key == 'deploy-and-setup':
                has_deploy_script = True
                print(f"  ⚠️  deploy-and-setup: {len(value)} bytes (NOT auto-run)")
            else:
                print(f"  📝 {key}: {len(str(value))} chars")
        
        if not has_startup_script:
            print("\n  ❌ MISSING: startup-script (won't run automatically!)")
        if has_deploy_script and not has_startup_script:
            print("\n  ⚠️  ISSUE: deploy-and-setup exists but startup-script is missing!")
            print("     This means deployment script won't run on boot.")
        
        # OS Login
        metadata_items_dict = {item.get('key'): item.get('value') for item in items}
        enable_oslogin = metadata_items_dict.get('enable-oslogin', 'FALSE')
        print(f"\nOS Login: {enable_oslogin}")
        
        # Network
        network_interfaces = instance.get('networkInterfaces', [])
        if network_interfaces:
            access_configs = network_interfaces[0].get('accessConfigs', [])
            if access_configs:
                external_ip = access_configs[0].get('natIP', 'N/A')
                print(f"External IP: {external_ip}")
        
        # Tags
        tags = instance.get('tags', {})
        if tags:
            items_list = tags.get('items', [])
            if items_list:
                print(f"\nTags: {', '.join(items_list)}")
        
        # Machine Type
        machine_type = instance.get('machineType', '').split('/')[-1]
        print(f"\nMachine Type: {machine_type}")
        
        # Zone
        zone = instance.get('zone', '').split('/')[-1]
        print(f"Zone: {zone}")

if __name__ == "__main__":
    try:
        compare_vms()
        
        print("\n" + "="*80)
        print("DIAGNOSIS SUMMARY")
        print("="*80)
        print("\nIf 'real-time-inventory' is missing startup-script:")
        print("  → This is why deployment isn't happening automatically")
        print("  → Other VMs likely have startup-script set")
        print("\nSolution:")
        print("  1. Set startup-script metadata (via API or gcloud)")
        print("  2. OR manually run: curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-and-setup | bash")
        print("  3. OR use gcloud compute scp to deploy files directly")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
