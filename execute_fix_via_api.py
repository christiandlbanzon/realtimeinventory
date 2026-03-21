#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Execute the fix script on VM using Compute Engine API
"""

import base64
import sys
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

def execute_via_startup_script():
    """Execute command via startup script metadata"""
    compute_service = get_compute_service()
    if not compute_service:
        return False
    
    # Read the fix script
    with open('apply_fix_on_vm.py', 'r', encoding='utf-8') as f:
        fix_script_content = f.read()
    
    # Encode as base64
    script_b64 = base64.b64encode(fix_script_content.encode('utf-8')).decode('utf-8')
    
    # Create startup script that runs the fix
    startup_script = f"""#!/bin/bash
cd /home/banzo
python3 apply_fix_on_vm.py
"""
    
    print("="*80)
    print("EXECUTING FIX VIA VM METADATA")
    print("="*80)
    print()
    print("⚠️  Note: This method requires VM restart or using instance metadata.")
    print("   Since the file is already on VM, it's easier to SSH manually.")
    print()
    print("The file is already copied. Just SSH and run:")
    print("  gcloud compute ssh inventory-updater-vm --zone=us-central1-a")
    print("  cd /home/banzo")
    print("  python3 apply_fix_on_vm.py")
    
    return False

if __name__ == "__main__":
    print("Since gcloud has issues, the easiest way is:")
    print()
    print("1. The file is already on VM (copy succeeded!)")
    print("2. SSH manually:")
    print("   gcloud compute ssh inventory-updater-vm --zone=us-central1-a")
    print("3. Then run:")
    print("   cd /home/banzo")
    print("   python3 apply_fix_on_vm.py")
    print()
    print("OR try the gcloud command again (sometimes it works):")
    print('   gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && python3 apply_fix_on_vm.py"')
