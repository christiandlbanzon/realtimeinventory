#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run VM fix using Compute Engine API directly
Bypasses gcloud CLI completely by using Python API with service account
"""

import sys
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2
import paramiko
import time

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

VM_NAME = "inventory-updater-vm"
VM_ZONE = "us-central1-a"
VM_PROJECT = "boxwood-chassis-332307"
SERVICE_ACCOUNT_FILE = "service-account-key.json"

print("="*80)
print("RUNNING VM FIX VIA COMPUTE ENGINE API (NO GCLOUD NEEDED)")
print("="*80)
print()

def get_compute_service():
    """Get Compute Engine API service using service account"""
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        # Disable proxy for API calls
        http = httplib2.Http(proxy_info=None)
        authorized_http = AuthorizedHttp(creds, http=http)
        service = build('compute', 'v1', http=authorized_http)
        return service
    except Exception as e:
        print(f"❌ Cannot create Compute service: {e}")
        return None

def get_vm_info(compute_service):
    """Get VM instance info including external IP"""
    try:
        instance = compute_service.instances().get(
            project=VM_PROJECT,
            zone=VM_ZONE,
            instance=VM_NAME
        ).execute()
        
        status = instance.get('status', 'UNKNOWN')
        print(f"✅ VM Status: {status}")
        
        if status != 'RUNNING':
            print(f"❌ VM is not running (status: {status})")
            return None
        
        network_interfaces = instance.get('networkInterfaces', [])
        if not network_interfaces:
            print("❌ No network interfaces found")
            return None
        
        access_configs = network_interfaces[0].get('accessConfigs', [])
        if not access_configs:
            print("❌ No external IP found")
            return None
        
        external_ip = access_configs[0].get('natIP')
        if not external_ip:
            print("❌ External IP is None")
            return None
        
        print(f"✅ VM IP: {external_ip}")
        return external_ip
        
    except Exception as e:
        print(f"❌ Error getting VM info: {e}")
        import traceback
        traceback.print_exc()
        return None

def ssh_via_api(compute_service, external_ip):
    """Use Compute Engine API to get SSH keys, then connect via paramiko"""
    print()
    print("Attempting SSH via API...")
    print("⚠️  Note: This requires OS Login or SSH keys to be set up")
    print()
    
    # Unfortunately, Compute Engine API doesn't provide direct SSH access
    # We need to use gcloud's SSH key generation or have keys already set up
    print("❌ Direct SSH via API requires OS Login or pre-configured SSH keys")
    print()
    print("ALTERNATIVE: Use gcloud with service account (if permissions fixed)")
    print("   OR manually SSH to the VM")
    return False

def try_gcloud_with_service_account():
    """Try gcloud with GOOGLE_APPLICATION_CREDENTIALS set"""
    import subprocess
    
    print("Trying gcloud with service account credentials...")
    print()
    
    # Set environment variable
    env = os.environ.copy()
    env['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath(SERVICE_ACCOUNT_FILE)
    
    # Try to use a custom config directory that we can write to
    temp_config = os.path.join(os.getcwd(), ".gcloud_temp_config")
    os.makedirs(temp_config, exist_ok=True)
    env['CLOUDSDK_CONFIG'] = temp_config
    
    gcloud_path = r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    if not os.path.exists(gcloud_path):
        gcloud_path = "gcloud"
    
    vm_name = "inventory-updater-vm"
    zone = "us-central1-a"
    command = "cd /home/banzo && python3 apply_fix_on_vm.py"
    
    try:
        print(f"Using custom config directory: {temp_config}")
        print(f"Executing SSH command...")
        print()
        
        result = subprocess.run(
            [gcloud_path, "compute", "ssh", vm_name,
             f"--zone={zone}",
             f"--command={command}"],
            env=env,
            timeout=60,
            text=True,
            capture_output=True
        )
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print()
            print("="*80)
            print("✅ FIX APPLIED SUCCESSFULLY!")
            print("="*80)
            return True
        else:
            print(f"❌ Failed with exit code: {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # First, try gcloud with custom config directory
    print("ATTEMPT 1: Using gcloud with custom config directory")
    print("="*80)
    if try_gcloud_with_service_account():
        sys.exit(0)
    
    print()
    print("="*80)
    print("ATTEMPT 2: Getting VM info via API")
    print("="*80)
    
    compute_service = get_compute_service()
    if compute_service:
        external_ip = get_vm_info(compute_service)
        if external_ip:
            print()
            print("="*80)
            print("MANUAL SSH OPTION")
            print("="*80)
            print()
            print(f"VM is running at: {external_ip}")
            print()
            print("You can SSH manually:")
            print(f"  ssh banzo@{external_ip}")
            print()
            print("Then run:")
            print("  cd /home/banzo")
            print("  python3 apply_fix_on_vm.py")
            print()
    
    print()
    print("="*80)
    print("RECOMMENDATION")
    print("="*80)
    print()
    print("The gcloud installation has permission issues that prevent it from")
    print("writing to credentials.db. The best solution is to reinstall gcloud.")
    print()
    print("See: SIMPLE_REINSTALL_STEPS.md")
    print()
