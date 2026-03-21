#!/usr/bin/env python3
"""
Rename VM from inventory-updater-vm-new to real-time-inventory
"""

import os
import sys
import time

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
OLD_VM_NAME = "inventory-updater-vm-new"
NEW_VM_NAME = "real-time-inventory"
SERVICE_ACCOUNT_FILE = "service-account-key.json"

def rename_vm():
    """Rename the VM"""
    print("="*80)
    print("RENAMING VM")
    print("="*80)
    print(f"\nOld Name: {OLD_VM_NAME}")
    print(f"New Name: {NEW_VM_NAME}")
    print(f"Zone: {ZONE}")
    print(f"Project: {PROJECT_ID}")
    
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
        
        print("\n✅ Authenticated")
    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        return False
    
    # Check if old VM exists
    try:
        print(f"\n[1/4] Checking old VM: {OLD_VM_NAME}...")
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=OLD_VM_NAME
        ).execute()
        
        status = instance.get('status', 'UNKNOWN')
        print(f"   Status: {status}")
        
        if status == 'RUNNING':
            print(f"\n⚠️  VM is RUNNING. Stopping it first...")
            compute.instances().stop(
                project=PROJECT_ID,
                zone=ZONE,
                instance=OLD_VM_NAME
            ).execute()
            
            print("   Waiting for VM to stop...")
            for i in range(30):
                time.sleep(2)
                instance = compute.instances().get(
                    project=PROJECT_ID,
                    zone=ZONE,
                    instance=OLD_VM_NAME
                ).execute()
                if instance.get('status') == 'TERMINATED':
                    print("   ✅ VM stopped")
                    break
            else:
                print("   ⚠️  VM may still be stopping")
        
    except Exception as e:
        if "not found" in str(e).lower():
            print(f"\n❌ VM '{OLD_VM_NAME}' not found!")
            return False
        else:
            print(f"\n❌ Error checking VM: {e}")
            return False
    
    # Check if new name already exists
    try:
        print(f"\n[2/4] Checking if '{NEW_VM_NAME}' already exists...")
        existing = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=NEW_VM_NAME
        ).execute()
        print(f"   ⚠️  VM '{NEW_VM_NAME}' already exists!")
        print(f"   Status: {existing.get('status')}")
        response = input("   Delete it and rename? (yes/no): ")
        if response.lower() == 'yes':
            print("   Deleting existing VM...")
            compute.instances().delete(
                project=PROJECT_ID,
                zone=ZONE,
                instance=NEW_VM_NAME
            ).execute()
            print("   Waiting for deletion...")
            time.sleep(10)
        else:
            print("   Cancelled")
            return False
    except Exception as e:
        if "not found" in str(e).lower():
            print("   ✅ New name is available")
        else:
            print(f"   ⚠️  Error checking: {e}")
    
    # Rename VM
    try:
        print(f"\n[3/4] Renaming VM...")
        # Wait a bit for VM to fully stop
        print("   Waiting for VM to be fully stopped...")
        time.sleep(5)
        
        # Get fresh instance data
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=OLD_VM_NAME
        ).execute()
        
        # Retry logic for rename
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Get current instance name to include in request
                current_instance = compute.instances().get(
                    project=PROJECT_ID,
                    zone=ZONE,
                    instance=OLD_VM_NAME
                ).execute()
                current_name = current_instance.get('name', OLD_VM_NAME)
                
                operation = compute.instances().setName(
                    project=PROJECT_ID,
                    zone=ZONE,
                    instance=OLD_VM_NAME,
                    body={
                        'name': NEW_VM_NAME,
                        'currentName': current_name  # Required: current name to prevent conflicts
                    }
                ).execute()
                break
            except Exception as e:
                if attempt < max_retries - 1 and "412" in str(e):
                    print(f"   ⚠️  Retry {attempt + 1}/{max_retries}...")
                    time.sleep(3)
                    # Refresh instance
                    instance = compute.instances().get(
                        project=PROJECT_ID,
                        zone=ZONE,
                        instance=OLD_VM_NAME
                    ).execute()
                else:
                    raise
        
        print(f"   ✅ Rename operation started")
        print(f"   Operation: {operation['name']}")
        
        # Wait for rename to complete
        print("   Waiting for rename to complete...")
        for i in range(30):
            time.sleep(2)
            op = compute.zoneOperations().get(
                project=PROJECT_ID,
                zone=ZONE,
                operation=operation['name']
            ).execute()
            
            if op['status'] == 'DONE':
                if 'error' in op:
                    print(f"   ❌ Error: {op['error']}")
                    return False
                print("   ✅ VM renamed successfully!")
                break
        else:
            print("   ⚠️  Rename taking longer than expected")
        
    except Exception as e:
        print(f"\n❌ Error renaming VM: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Start VM
    try:
        print(f"\n[4/4] Starting VM with new name...")
        compute.instances().start(
            project=PROJECT_ID,
            zone=ZONE,
            instance=NEW_VM_NAME
        ).execute()
        
        print("   ✅ VM start initiated")
        print("   Waiting for VM to start...")
        
        for i in range(30):
            time.sleep(2)
            instance = compute.instances().get(
                project=PROJECT_ID,
                zone=ZONE,
                instance=NEW_VM_NAME
            ).execute()
            
            if instance.get('status') == 'RUNNING':
                print("   ✅ VM is running with new name!")
                break
        else:
            print("   ⚠️  VM may still be starting")
        
    except Exception as e:
        print(f"\n⚠️  Error starting VM: {e}")
        print("   You can start it manually later")
    
    print("\n" + "="*80)
    print("✅ VM RENAMED SUCCESSFULLY")
    print("="*80)
    print(f"\nOld Name: {OLD_VM_NAME}")
    print(f"New Name: {NEW_VM_NAME}")
    print(f"\nYou can now use:")
    print(f"  gcloud compute ssh {NEW_VM_NAME} --zone={ZONE} --project={PROJECT_ID}")
    
    return True

if __name__ == "__main__":
    try:
        success = rename_vm()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
