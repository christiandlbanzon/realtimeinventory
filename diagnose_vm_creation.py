#!/usr/bin/env python3
"""Diagnose VM creation issues"""

import os
import sys

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

PROJECT_ID = "boxwood-chassis-332307"
ZONE = "us-central1-a"
VM_NAME = "real-time-inventory"
SERVICE_ACCOUNT_FILE = "service-account-key.json"

print("="*80)
print("DIAGNOSING VM CREATION")
print("="*80)

# Check credentials
print("\n[1/5] Checking credentials...")
if not os.path.exists(SERVICE_ACCOUNT_FILE):
    print(f"   ERROR: {SERVICE_ACCOUNT_FILE} not found!")
    sys.exit(1)
print(f"   OK: {SERVICE_ACCOUNT_FILE} exists")

# Authenticate
print("\n[2/5] Testing authentication...")
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
    print("   OK: Authentication successful")
except Exception as e:
    print(f"   ERROR: Authentication failed: {e}")
    sys.exit(1)

# List VMs in zone
print("\n[3/5] Listing VMs in zone...")
try:
    instances = compute.instances().list(project=PROJECT_ID, zone=ZONE).execute()
    if 'items' in instances:
        print(f"   Found {len(instances['items'])} VM(s):")
        for inst in instances['items']:
            print(f"     - {inst['name']} ({inst.get('status', 'UNKNOWN')})")
    else:
        print("   No VMs found in this zone")
except Exception as e:
    print(f"   ERROR: {e}")

# Check if target VM exists
print(f"\n[4/5] Checking if '{VM_NAME}' exists...")
try:
    instance = compute.instances().get(
        project=PROJECT_ID,
        zone=ZONE,
        instance=VM_NAME
    ).execute()
    print(f"   VM EXISTS!")
    print(f"   Status: {instance.get('status')}")
    print(f"   Machine Type: {instance.get('machineType', '').split('/')[-1]}")
    
    # Check metadata
    metadata = instance.get('metadata', {}).get('items', [])
    has_startup = any(item.get('key') == 'startup-script' for item in metadata)
    print(f"   Has startup-script: {has_startup}")
    
    if instance.get('status') == 'RUNNING':
        print("\n   VM is RUNNING!")
        print("   Check logs: gcloud compute ssh real-time-inventory --zone=us-central1-a --command='tail -50 /var/log/startup.log'")
        print("   Check cron: gcloud compute ssh real-time-inventory --zone=us-central1-a --command='crontab -l'")
    
except Exception as e:
    if "not found" in str(e).lower():
        print(f"   VM does not exist")
    else:
        print(f"   ERROR: {e}")

# Test API permissions
print("\n[5/5] Testing API permissions...")
try:
    # Try to list zones (read permission)
    zones = compute.zones().list(project=PROJECT_ID).execute()
    print(f"   OK: Can list zones ({len(zones.get('items', []))} zones)")
    
    # Try to get zone info (read permission)
    zone_info = compute.zones().get(project=PROJECT_ID, zone=ZONE).execute()
    print(f"   OK: Can access zone '{ZONE}'")
    
    print("\n   NOTE: To create VMs, service account needs:")
    print("   - roles/compute.instanceAdmin.v1")
    print("   - roles/iam.serviceAccountUser")
    
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "="*80)
print("DIAGNOSIS COMPLETE")
print("="*80)
