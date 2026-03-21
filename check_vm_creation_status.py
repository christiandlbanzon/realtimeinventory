#!/usr/bin/env python3
"""Check if VM was created successfully"""

import sys
import os

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

PROJECT_ID = "boxwood-chassis-332307"
# Check both possible VMs
ZONES_TO_CHECK = ["us-east1-b", "us-central1-b"]
VM_NAMES_TO_CHECK = ["real-time-inventory-v2", "real-time-inventory"]

try:
    creds = service_account.Credentials.from_service_account_file(
        "service-account-key.json",
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    http = httplib2.Http(proxy_info=None)
    auth_http = AuthorizedHttp(creds, http=http)
    compute = build('compute', 'v1', http=auth_http)
    
    instance = compute.instances().get(
        project=PROJECT_ID,
        zone=ZONE,
        instance=VM_NAME
    ).execute()
    
    status = instance.get('status')
    print(f"✅ VM '{VM_NAME}' exists!")
    print(f"   Status: {status}")
    
    # Check metadata
    metadata = instance.get('metadata', {}).get('items', [])
    has_startup = any(item.get('key') == 'startup-script' for item in metadata)
    print(f"   Has startup-script: {has_startup}")
    
except Exception as e:
    if "not found" in str(e).lower():
        print(f"VM '{VM_NAME}' not found yet")
    else:
        print(f"Error: {e}")
