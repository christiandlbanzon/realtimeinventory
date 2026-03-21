#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply VM fix using Compute Engine API directly
Bypasses gcloud permission issues
"""

import json
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
SCRIPT_PATH = "/home/banzo/vm_inventory_updater.py"

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

def execute_command_on_vm(compute_service, command):
    """Execute a command on VM using Compute Engine API"""
    try:
        # Use the instances().executeCommand() method if available
        # Otherwise, we'll need to use a different approach
        
        # For now, let's create a startup script approach or use serial port
        # Actually, the best way is to use gcloud compute ssh, but since that's failing,
        # let's try using the instance's metadata to pass a script
        
        # Alternative: Use the serial port to read output, but we can't execute commands that way
        
        # Best approach: Create a script file and use metadata startup script
        # But that requires VM restart...
        
        # Actually, let me try using the OS Login API or direct SSH via API
        # The Compute Engine API doesn't have a direct "execute command" endpoint
        
        # For now, let's create instructions and a script file that can be manually copied
        print("⚠️  Direct command execution via API requires OS Login setup")
        print("   Creating fix script that can be copied to VM...")
        return False, "API doesn't support direct command execution"
        
    except Exception as e:
        return False, str(e)

def create_fix_script_file():
    """Create the fix script as a file"""
    fix_script = """#!/usr/bin/env python3
import re
import shutil
from datetime import datetime

script_file = "/home/banzo/vm_inventory_updater.py"
backup_file = f"{script_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

print("="*80)
print("APPLYING PROMOTION QUANTITY FIX")
print("="*80)
print()

print(f"Script file: {script_file}")
print(f"Backup file: {backup_file}")
print()

print("Reading script file...")
with open(script_file, 'r', encoding='utf-8') as f:
    content = f.read()

if "FIX FOR PROMOTION ITEMS" in content:
    print("⚠️  Fix already applied!")
    exit(0)

shutil.copy(script_file, backup_file)
print(f"✅ Backup created: {backup_file}")

pattern = r'(# SAFEGUARD: Each line item represents 1 unit sold.*?quantity = 1)'
replacement = '''# SAFEGUARD: Each line item represents 1 unit sold (Clover API doesn't have quantity field)
                    # FIX FOR PROMOTION ITEMS: Items in promotions have quantity=0 but still count as 1 unit
                    # Check if quantity exists and is valid, otherwise default to 1
                    api_quantity = item.get('quantity', 0)
                    if api_quantity == 0:
                        # Promotion items have quantity=0 but each line item = 1 unit sold
                        quantity = 1
                    else:
                        # Normal items: convert from millis to units (1000 millis = 1 unit)
                        quantity = int(api_quantity / 1000) if api_quantity > 0 else 1
                    
                    # Ensure minimum of 1 unit per line item (safety check)
                    quantity = max(quantity, 1)'''

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

if new_content != content:
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("✅ Fix applied successfully!")
    
    print("\\nVerification:")
    with open(script_file, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if "FIX FOR PROMOTION ITEMS" in line:
                for j in range(i, min(i+12, len(lines))):
                    print(f"{j+1:4d}: {lines[j].rstrip()}")
                break
else:
    print("❌ Could not find pattern to replace")
    exit(1)

print("\\n✅ Fix complete!")
"""
    
    with open('apply_fix_on_vm.py', 'w', encoding='utf-8') as f:
        f.write(fix_script)
    
    print("✅ Created apply_fix_on_vm.py")
    return True

def main():
    print("="*80)
    print("APPLY VM FIX VIA API")
    print("="*80)
    print()
    
    compute_service = get_compute_service()
    if not compute_service:
        print("❌ Cannot access Compute Engine API")
        return
    
    # Check VM status
    print("[1] Checking VM status...")
    try:
        instance = compute_service.instances().get(
            project=VM_PROJECT,
            zone=VM_ZONE,
            instance=VM_NAME
        ).execute()
        
        status = instance.get('status', 'UNKNOWN')
        print(f"✅ VM Status: {status}")
        
        if status != 'RUNNING':
            print("⚠️  VM is not running - cannot apply fix")
            return
    except Exception as e:
        print(f"❌ Error checking VM: {e}")
        return
    
    print()
    print("[2] Creating fix script...")
    create_fix_script_file()
    
    print()
    print("="*80)
    print("NEXT STEPS")
    print("="*80)
    print()
    print("Due to gcloud permission issues, please run these commands manually:")
    print()
    print("1. Copy fix script to VM:")
    print(f"   gcloud compute scp apply_fix_on_vm.py {VM_NAME}:/home/banzo/ --zone={VM_ZONE}")
    print()
    print("2. SSH to VM:")
    print(f"   gcloud compute ssh {VM_NAME} --zone={VM_ZONE}")
    print()
    print("3. Run the fix:")
    print("   cd /home/banzo")
    print("   python3 apply_fix_on_vm.py")
    print()
    print("OR use the script I created: apply_fix_on_vm.py")
    print("(It's already in this directory and ready to copy)")

if __name__ == "__main__":
    main()
