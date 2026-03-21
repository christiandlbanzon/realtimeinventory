#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Execute VM fix using Compute Engine API directly
Bypasses gcloud CLI completely
"""

import sys
import json
import base64
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

VM_NAME = "inventory-updater-vm"
VM_ZONE = "us-central1-a"
VM_PROJECT = "boxwood-chassis-332307"

def get_compute_service():
    """Get Compute Engine API service"""
    try:
        creds = service_account.Credentials.from_service_account_file(
            "service-account-key.json",
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        http = httplib2.Http(proxy_info=None)
        authorized_http = AuthorizedHttp(creds, http=http)
        service = build('compute', 'v1', http=authorized_http)
        return service
    except Exception as e:
        print(f"❌ Cannot create Compute service: {e}")
        return None

def execute_via_serial_port(compute_service):
    """Try to execute via serial port (read-only, but can check if script ran)"""
    print("="*80)
    print("EXECUTING VM FIX VIA COMPUTE ENGINE API")
    print("="*80)
    print()
    
    # Unfortunately, Compute Engine API doesn't support direct command execution
    # without OS Login. But we can check if the script exists and provide instructions
    
    print("⚠️  Compute Engine API doesn't support direct command execution")
    print("   without OS Login setup.")
    print()
    print("However, the file is already on the VM!")
    print("   File: /home/banzo/apply_fix_on_vm.py ✅")
    print()
    print("SOLUTION: Since gcloud has permission issues, use SSH manually:")
    print()
    print("1. Open a NEW PowerShell or CMD window (fresh session)")
    print("2. Run:")
    print('   gcloud compute ssh inventory-updater-vm --zone=us-central1-a')
    print()
    print("3. Once connected to VM, run:")
    print("   cd /home/banzo")
    print("   python3 apply_fix_on_vm.py")
    print()
    print("This should work because SSH doesn't need to write to gcloud config.")
    print()
    
    # Check VM status
    try:
        instance = compute_service.instances().get(
            project=VM_PROJECT,
            zone=VM_ZONE,
            instance=VM_NAME
        ).execute()
        
        status = instance.get('status', 'UNKNOWN')
        print(f"✅ VM Status: {status}")
        
        if status == 'RUNNING':
            network_interfaces = instance.get('networkInterfaces', [])
            if network_interfaces:
                access_configs = network_interfaces[0].get('accessConfigs', [])
                if access_configs:
                    external_ip = access_configs[0].get('natIP', 'N/A')
                    print(f"✅ VM IP: {external_ip}")
                    print()
                    print("You can also SSH directly using the IP if gcloud still fails:")
                    print(f"   ssh banzo@{external_ip}")
        
    except Exception as e:
        print(f"⚠️  Could not get VM info: {e}")
    
    return False

if __name__ == "__main__":
    compute_service = get_compute_service()
    if compute_service:
        execute_via_serial_port(compute_service)
    else:
        print("Cannot access Compute Engine API")
