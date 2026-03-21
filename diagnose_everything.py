#!/usr/bin/env python3
"""Complete diagnostic - check everything before we proceed"""

import os
import sys
import json

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

print("="*80)
print("COMPLETE SYSTEM DIAGNOSTIC")
print("="*80)

# 1. Check files exist
print("\n[1/7] Checking required files...")
REQUIRED_FILES = {
    "vm_inventory_updater_fixed.py": "Main Python script",
    "clover_creds.json": "Clover API credentials",
    "service-account-key.json": "Google Cloud service account"
}

all_files_exist = True
for filename, description in REQUIRED_FILES.items():
    if os.path.exists(filename):
        size = os.path.getsize(filename)
        print(f"  OK: {filename} ({size:,} bytes) - {description}")
    else:
        print(f"  ERROR: {filename} NOT FOUND - {description}")
        all_files_exist = False

if not all_files_exist:
    print("\nERROR: Missing required files!")
    sys.exit(1)

# 2. Check service account JSON
print("\n[2/7] Validating service account...")
try:
    with open("service-account-key.json", 'r') as f:
        sa_data = json.load(f)
    
    project_id = sa_data.get('project_id', 'NOT FOUND')
    client_email = sa_data.get('client_email', 'NOT FOUND')
    print(f"  Project ID: {project_id}")
    print(f"  Service Account: {client_email}")
    
    if project_id != "boxwood-chassis-332307":
        print(f"  WARNING: Project ID mismatch! Expected 'boxwood-chassis-332307'")
    
except Exception as e:
    print(f"  ERROR: Invalid JSON: {e}")
    sys.exit(1)

# 3. Check Python script for February sheet ID
print("\n[3/7] Checking Python script configuration...")
try:
    with open("vm_inventory_updater_fixed.py", 'r', encoding='utf-8') as f:
        script_content = f.read()
    
    if "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4" in script_content:
        print("  OK: February sheet ID found in script")
    else:
        print("  WARNING: February sheet ID NOT found!")
    
    if "current_month >= 2" in script_content:
        print("  OK: Month detection logic found")
    else:
        print("  WARNING: Month detection logic NOT found!")
        
except Exception as e:
    print(f"  ERROR: {e}")

# 4. Check startup script size
print("\n[4/7] Checking startup script...")
if os.path.exists("startup_script.sh"):
    size = os.path.getsize("startup_script.sh")
    print(f"  Size: {size:,} bytes ({size/1024:.1f} KB)")
    
    # Google Cloud limit is 256 KB for metadata values
    if size > 256 * 1024:
        print(f"  ERROR: Startup script exceeds 256 KB limit!")
    elif size > 200 * 1024:
        print(f"  WARNING: Startup script is large ({size/1024:.1f} KB) - close to 256 KB limit")
    else:
        print(f"  OK: Size is reasonable")
else:
    print("  WARNING: startup_script.sh not found")

# 5. Test Google Cloud authentication
print("\n[5/7] Testing Google Cloud authentication...")
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2
    
    credentials = service_account.Credentials.from_service_account_file(
        "service-account-key.json",
        scopes=['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/compute']
    )
    
    http = httplib2.Http(proxy_info=None, timeout=10)
    authorized_http = AuthorizedHttp(credentials, http=http)
    compute = build('compute', 'v1', http=authorized_http)
    
    print("  OK: Authentication successful")
    
except Exception as e:
    print(f"  ERROR: Authentication failed: {e}")
    sys.exit(1)

# 6. Test API read access
print("\n[6/7] Testing API read access...")
PROJECT_ID = "boxwood-chassis-332307"
ZONES_TO_TEST = ["us-east1-b", "us-central1-b", "us-central1-a"]

for zone in ZONES_TO_TEST:
    try:
        instances = compute.instances().list(project=PROJECT_ID, zone=zone).execute()
        vm_list = instances.get('items', [])
        print(f"  OK: Can read zone {zone} ({len(vm_list)} VMs found)")
    except Exception as e:
        error_str = str(e)
        if "503" in error_str:
            print(f"  ERROR: Zone {zone} - 503 Service Unavailable")
        else:
            print(f"  ERROR: Zone {zone} - {e}")

# 7. Check for existing VMs
print("\n[7/7] Checking for existing VMs...")
existing_vms = []
for zone in ZONES_TO_TEST:
    try:
        instances = compute.instances().list(project=PROJECT_ID, zone=zone).execute()
        for vm in instances.get('items', []):
            if 'real-time-inventory' in vm['name'].lower():
                existing_vms.append({
                    'name': vm['name'],
                    'zone': zone,
                    'status': vm.get('status', 'UNKNOWN')
                })
    except:
        pass

if existing_vms:
    print("  Found existing VMs:")
    for vm in existing_vms:
        print(f"    - {vm['name']} in {vm['zone']} ({vm['status']})")
else:
    print("  No existing 'real-time-inventory' VMs found")

# Summary
print("\n" + "="*80)
print("DIAGNOSTIC SUMMARY")
print("="*80)

if all_files_exist:
    print("\nREADY TO PROCEED:")
    print("  1. All required files exist")
    print("  2. Service account is valid")
    print("  3. Python script is configured")
    
    if existing_vms:
        print("\nRECOMMENDATION:")
        print("  Delete existing VMs first, then create fresh one")
    else:
        print("\nRECOMMENDATION:")
        print("  Create VM manually via Console (API is unreliable)")
        print(f"  https://console.cloud.google.com/compute/instances/create?project={PROJECT_ID}")
else:
    print("\nNOT READY:")
    print("  Fix missing files first")

print("\n" + "="*80)
