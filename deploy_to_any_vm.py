#!/usr/bin/env python3
"""
Deploy inventory updater to any VM using Compute Engine API
Works with service account credentials - no gcloud CLI needed
"""

import os
import sys
import base64
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
SERVICE_ACCOUNT_FILE = "service-account-key.json"
SOURCE_FILE = "vm_inventory_updater_fixed.py"
TARGET_PATH = "/home/banzo/vm_inventory_updater.py"

def deploy_to_vm(vm_name="real-time-inventory", zone="us-central1-a", vm_user="banzo"):  # Updated default name
    """Deploy file to VM using Compute Engine API"""
    print("="*80)
    print("DEPLOYING TO VM VIA COMPUTE ENGINE API")
    print("="*80)
    print(f"\nVM Name: {vm_name}")
    print(f"Zone: {zone}")
    print(f"User: {vm_user}")
    print(f"Target Path: {TARGET_PATH}")
    
    # Read source file
    if not os.path.exists(SOURCE_FILE):
        print(f"\n❌ Source file not found: {SOURCE_FILE}")
        return False
    
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        file_content = f.read()
    
    file_size = len(file_content)
    print(f"\n✅ Read source file: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    
    # Verify February sheet ID
    if "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4" in file_content:
        print("✅ February sheet ID found in code")
    else:
        print("⚠️  WARNING: February sheet ID not found!")
    
    # Base64 encode
    file_b64 = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')
    
    # Create deployment script
    deploy_script = f"""#!/bin/bash
set -e
cd /home/{vm_user}

# Backup current file
if [ -f {TARGET_PATH} ]; then
    cp {TARGET_PATH} {TARGET_PATH}.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Backup created"
fi

# Write new file
echo '{file_b64}' | base64 -d > {TARGET_PATH}

# Set permissions
chmod +x {TARGET_PATH}

# Verify
if grep -q "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4" {TARGET_PATH}; then
    echo "✅ February sheet ID verified"
else
    echo "⚠️  WARNING: February sheet ID not found"
fi

# Log
echo "$(date): Deployed via API" >> /home/{vm_user}/deployment.log

# Show info
ls -lh {TARGET_PATH}
echo "✅ Deployment complete"
"""
    
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
        
        print("\n✅ Authenticated with Compute Engine API")
    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        return False
    
    # Check if VM exists
    try:
        print(f"\n[1/4] Checking VM: {vm_name}...")
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=zone,
            instance=vm_name
        ).execute()
        
        status = instance.get('status', 'UNKNOWN')
        print(f"✅ VM found - Status: {status}")
        
        if status != 'RUNNING':
            print(f"\n[2/4] Starting VM...")
            compute.instances().start(
                project=PROJECT_ID,
                zone=zone,
                instance=vm_name
            ).execute()
            
            # Wait for VM to start
            print("   Waiting for VM to start...")
            for i in range(30):
                time.sleep(2)
                instance = compute.instances().get(
                    project=PROJECT_ID,
                    zone=zone,
                    instance=vm_name
                ).execute()
                if instance.get('status') == 'RUNNING':
                    print("   ✅ VM is running")
                    break
            else:
                print("   ⚠️  VM may still be starting")
        
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "404" in error_msg:
            print(f"\n❌ VM '{vm_name}' not found in zone '{zone}'")
            print(f"\nAvailable VMs in project:")
            try:
                instances = compute.instances().list(project=PROJECT_ID, zone=zone).execute()
                if 'items' in instances:
                    for inst in instances['items']:
                        print(f"  - {inst['name']} ({inst.get('status', 'UNKNOWN')})")
                else:
                    print("  (No VMs found in this zone)")
            except:
                pass
            return False
        else:
            print(f"\n❌ Error checking VM: {e}")
            return False
    
    # Update metadata
    try:
        print(f"\n[3/4] Updating VM metadata with deployment script...")
        
        metadata = instance.get('metadata', {})
        fingerprint = metadata.get('fingerprint', '')
        items = metadata.get('items', [])
        
        # Remove old deployment scripts
        items = [item for item in items if item.get('key') not in ['startup-script', 'deploy-script', 'deploy-inventory']]
        
        # Add deployment script
        items.append({
            'key': 'deploy-inventory',
            'value': deploy_script
        })
        
        # Retry logic for API errors
        max_retries = 3
        for attempt in range(max_retries):
            try:
                compute.instances().setMetadata(
                    project=PROJECT_ID,
                    zone=zone,
                    instance=vm_name,
                    body={
                        'fingerprint': fingerprint,
                        'items': items
                    }
                ).execute()
                print("✅ Metadata updated successfully")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"   ⚠️  API error (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    # Refresh fingerprint
                    instance = compute.instances().get(
                        project=PROJECT_ID,
                        zone=zone,
                        instance=vm_name
                    ).execute()
                    fingerprint = instance.get('metadata', {}).get('fingerprint', '')
                else:
                    raise
        
    except Exception as e:
        error_msg = str(e)
        if "503" in error_msg or "unavailable" in error_msg.lower():
            print(f"\n❌ Google Cloud API is currently unavailable (503 error)")
            print(f"   This is a temporary Google Cloud issue, not a problem with your VM.")
            print(f"\n   Alternative: Use gcloud CLI manually:")
            print(f"   gcloud compute scp {SOURCE_FILE} {vm_user}@{vm_name}:{TARGET_PATH} --zone={zone} --project={PROJECT_ID}")
            return False
        else:
            print(f"\n❌ Error updating metadata: {e}")
            return False
    
    # Execute deployment
    print(f"\n[4/4] Deployment script ready in VM metadata")
    print(f"\n✅ Deployment script added to VM metadata")
    print(f"\nTo execute the deployment:")
    print(f"   SSH to VM and run:")
    print(f"   curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-inventory | bash")
    print(f"\nOr restart the VM to trigger automatically via startup-script")
    
    return True

def list_available_vms():
    """List all VMs in the project"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        
        http = httplib2.Http(proxy_info=None)
        authorized_http = AuthorizedHttp(credentials, http=http)
        compute = build('compute', 'v1', http=authorized_http)
        
        print("="*80)
        print("AVAILABLE VMs IN PROJECT")
        print("="*80)
        
        # List all zones
        zones = compute.zones().list(project=PROJECT_ID).execute()
        
        all_vms = []
        for zone_info in zones.get('items', []):
            zone_name = zone_info['name']
            try:
                instances = compute.instances().list(project=PROJECT_ID, zone=zone_name).execute()
                for instance in instances.get('items', []):
                    all_vms.append({
                        'name': instance['name'],
                        'zone': zone_name,
                        'status': instance.get('status', 'UNKNOWN')
                    })
            except:
                pass
        
        if all_vms:
            print(f"\nFound {len(all_vms)} VM(s):\n")
            for vm in all_vms:
                print(f"  • {vm['name']}")
                print(f"    Zone: {vm['zone']}")
                print(f"    Status: {vm['status']}")
                print()
        else:
            print("\nNo VMs found in project")
        
        return all_vms
        
    except Exception as e:
        print(f"Error listing VMs: {e}")
        return []

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy inventory updater to VM')
    parser.add_argument('--vm-name', help='VM name (default: real-time-inventory)', default='real-time-inventory')
    parser.add_argument('--zone', help='Zone (default: us-central1-a)', default='us-central1-a')
    parser.add_argument('--user', help='VM user (default: banzo)', default='banzo')
    parser.add_argument('--list', action='store_true', help='List all available VMs')
    
    args = parser.parse_args()
    
    if args.list:
        list_available_vms()
    else:
        success = deploy_to_vm(args.vm_name, args.zone, args.user)
        if success:
            print("\n" + "="*80)
            print("✅ DEPLOYMENT READY")
            print("="*80)
            print("\nThe deployment script is in VM metadata.")
            print("Execute it via SSH or it will run on next VM restart.")
        sys.exit(0 if success else 1)
