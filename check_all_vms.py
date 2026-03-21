#!/usr/bin/env python3
"""Check for all real-time-inventory VMs"""

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
SERVICE_ACCOUNT_FILE = "service-account-key.json"

print("Checking for real-time-inventory VMs...")

try:
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    http = httplib2.Http(proxy_info=None)
    authorized_http = AuthorizedHttp(credentials, http=http)
    compute = build('compute', 'v1', http=authorized_http)
    
    # Check multiple zones
    zones_to_check = ['us-east1-b', 'us-central1-b', 'us-central1-a']
    found_vms = []
    
    for zone in zones_to_check:
        try:
            instances = compute.instances().list(project=PROJECT_ID, zone=zone).execute()
            for instance in instances.get('items', []):
                if 'real-time-inventory' in instance['name']:
                    found_vms.append({
                        'name': instance['name'],
                        'zone': zone,
                        'status': instance.get('status', 'UNKNOWN')
                    })
        except:
            pass
    
    if found_vms:
        print(f"\nFound {len(found_vms)} VM(s):")
        for vm in found_vms:
            print(f"  - {vm['name']} in {vm['zone']} ({vm['status']})")
    else:
        print("\nNo real-time-inventory VMs found")
        
except Exception as e:
    print(f"Error: {e}")
