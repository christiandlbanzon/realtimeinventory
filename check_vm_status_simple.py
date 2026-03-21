#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple VM status check using Python API only (no SSH required)
"""

import sys
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def check_vm_status():
    """Check VM status via Python API"""
    print("="*80)
    print("VM STATUS CHECK (via Python API)")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from google_auth_httplib2 import AuthorizedHttp
        import httplib2
        
        print("[1] Loading service account credentials...")
        credentials = service_account.Credentials.from_service_account_file(
            'service-account-key.json',
            scopes=['https://www.googleapis.com/auth/compute']
        )
        
        print("[2] Connecting to Compute Engine API...")
        # Disable proxy
        http = httplib2.Http(proxy_info=None)
        authorized_http = AuthorizedHttp(credentials, http=http)
        compute = build('compute', 'v1', http=authorized_http)
        
        print("[3] Getting VM instance information...")
        instance_info = compute.instances().get(
            project='boxwood-chassis-332307',
            zone='us-central1-a',
            instance='inventory-updater-vm'
        ).execute()
        
        status = instance_info.get('status')
        print(f"\n✅ VM Status: {status}")
        
        if status == 'RUNNING':
            # Get network info
            network_interfaces = instance_info.get('networkInterfaces', [])
            if network_interfaces:
                access_configs = network_interfaces[0].get('accessConfigs', [])
                if access_configs:
                    external_ip = access_configs[0].get('natIP', 'N/A')
                    print(f"   External IP: {external_ip}")
            
            # Get machine type
            machine_type = instance_info.get('machineType', '').split('/')[-1]
            print(f"   Machine Type: {machine_type}")
            
            # Get creation timestamp
            creation_timestamp = instance_info.get('creationTimestamp', '')
            if creation_timestamp:
                print(f"   Created: {creation_timestamp}")
            
            # Get zone
            zone = instance_info.get('zone', '').split('/')[-1]
            print(f"   Zone: {zone}")
            
            print("\n✅ VM is running and accessible!")
            print("\nNote: For detailed checks (logs, files, cron), SSH access is required.")
            print("   The VM is configured to run the inventory updater every 5 minutes.")
            
        else:
            print(f"\n⚠️  VM is not running (status: {status})")
        
        return status == 'RUNNING'
        
    except FileNotFoundError:
        print("\n❌ ERROR: service-account-key.json not found")
        print("   Make sure the service account key file exists in the current directory")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_credentials():
    """Check if credentials files exist locally"""
    print("\n" + "="*80)
    print("LOCAL CREDENTIALS CHECK")
    print("="*80)
    
    import os
    import json
    
    files_to_check = [
        ('service-account-key.json', 'Google Service Account'),
        ('clover_creds.json', 'Clover API Credentials'),
    ]
    
    all_ok = True
    for filename, description in files_to_check:
        if os.path.exists(filename):
            print(f"✅ {description}: Found")
            
            # Try to validate JSON
            if filename.endswith('.json'):
                try:
                    with open(filename, 'r') as f:
                        data = json.load(f)
                    if filename == 'clover_creds.json':
                        if isinstance(data, list):
                            print(f"   Found {len(data)} Clover locations")
                        else:
                            print("   ⚠️  Invalid format (should be a list)")
                    elif filename == 'service-account-key.json':
                        if data.get('type') == 'service_account':
                            print(f"   Project: {data.get('project_id', 'N/A')}")
                        else:
                            print("   ⚠️  Invalid service account format")
                except json.JSONDecodeError:
                    print(f"   ⚠️  Invalid JSON")
                    all_ok = False
        else:
            print(f"❌ {description}: NOT FOUND")
            all_ok = False
    
    return all_ok

if __name__ == "__main__":
    print("\n")
    creds_ok = check_credentials()
    vm_ok = check_vm_status()
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Local Credentials: {'✅ OK' if creds_ok else '❌ Missing/Invalid'}")
    print(f"VM Status: {'✅ RUNNING' if vm_ok else '❌ Not Running'}")
    
    if creds_ok and vm_ok:
        print("\n✅ System appears to be configured correctly!")
        print("   The inventory updater should be running on the VM every 5 minutes.")
    else:
        print("\n⚠️  Some issues detected. Please check the errors above.")
    
    print("="*80 + "\n")
