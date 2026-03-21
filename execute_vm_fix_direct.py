#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Execute VM fix directly using Compute Engine API
Bypasses gcloud CLI entirely
"""

import sys
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

def execute_via_metadata(compute_service):
    """Execute command via VM metadata startup script"""
    print("="*80)
    print("EXECUTING VM FIX VIA COMPUTE ENGINE API")
    print("="*80)
    print()
    
    # Read the fix script
    try:
        with open('apply_fix_on_vm.py', 'r', encoding='utf-8') as f:
            fix_script = f.read()
    except Exception as e:
        print(f"❌ Cannot read fix script: {e}")
        return False
    
    # Create a command that will execute the fix script
    # Since the file is already on VM, we just need to run it
    command = "cd /home/banzo && python3 apply_fix_on_vm.py"
    
    # Encode command as base64 for metadata
    command_b64 = base64.b64encode(command.encode('utf-8')).decode('utf-8')
    
    # Use the instances().setMetadata method to add a startup script
    # But this requires VM restart, so let's try a different approach
    
    # Actually, Compute Engine API doesn't have direct command execution
    # We need to use OS Login API or SSH keys
    
    print("⚠️  Compute Engine API doesn't support direct command execution")
    print("   without OS Login or SSH key setup.")
    print()
    print("Since the file is already on the VM, the easiest way is:")
    print("   1. SSH to VM manually: gcloud compute ssh inventory-updater-vm --zone=us-central1-a")
    print("   2. Run: cd /home/banzo && python3 apply_fix_on_vm.py")
    print()
    print("OR if you have SSH keys, I can help set up direct SSH access.")
    
    return False

def check_vm_status(compute_service):
    """Check VM is running"""
    try:
        instance = compute_service.instances().get(
            project=VM_PROJECT,
            zone=VM_ZONE,
            instance=VM_NAME
        ).execute()
        
        status = instance.get('status', 'UNKNOWN')
        if status == 'RUNNING':
            print(f"✅ VM is running")
            return True
        else:
            print(f"⚠️  VM status: {status}")
            return False
    except Exception as e:
        print(f"❌ Cannot check VM: {e}")
        return False

if __name__ == "__main__":
    print()
    
    compute_service = get_compute_service()
    if not compute_service:
        sys.exit(1)
    
    # Check VM status
    if not check_vm_status(compute_service):
        print("VM is not running - cannot execute fix")
        sys.exit(1)
    
    print()
    print("The file apply_fix_on_vm.py is already on the VM.")
    print("Since gcloud has permission issues, here are your options:")
    print()
    print("OPTION 1: Fix gcloud credentials.db file permissions")
    print("  1. Go to: C:\\Users\\banzo\\AppData\\Roaming\\gcloud")
    print("  2. Right-click credentials.db → Properties → Security")
    print("  3. Give your user Full Control")
    print("  4. Then run: gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command=\"cd /home/banzo && python3 apply_fix_on_vm.py\"")
    print()
    print("OPTION 2: SSH manually (most reliable)")
    print("  gcloud compute ssh inventory-updater-vm --zone=us-central1-a")
    print("  cd /home/banzo")
    print("  python3 apply_fix_on_vm.py")
    print()
    print("OPTION 3: Use SSH keys directly")
    print("  If you have SSH keys set up, I can help use them to connect directly")
