#!/usr/bin/env python3
"""Check scheduler execution details to get exact error"""

import os
import sys

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'service-account-key.json'

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2
import json

PROJECT_ID = "boxwood-chassis-332307"
REGION = "us-east1"
JOB_NAME = "inventory-updater"

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)

print("="*80)
print("CHECKING SCHEDULER EXECUTION DETAILS")
print("="*80)
print("\nLet's see what the scheduler is actually reporting.")
print()

scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

try:
    # Get scheduler details
    sched = scheduler.projects().locations().jobs().get(name=scheduler_name).execute()
    
    print("Scheduler Status:")
    print(f"  State: {sched.get('state')}")
    print(f"  Last Attempt: {sched.get('lastAttemptTime', 'N/A')}")
    print(f"  Status Code: {sched.get('status', {}).get('code', 'N/A')}")
    print(f"  Status Message: {sched.get('status', {}).get('message', 'N/A')}")
    
    # Check if there's error details
    status = sched.get('status', {})
    if status.get('code') != 0:
        print(f"\nERROR DETECTED:")
        print(f"  Code: {status.get('code')}")
        print(f"  Message: {status.get('message')}")
        print(f"  Details: {status.get('details', [])}")
    
    # Try to get execution history via locations API
    print("\n" + "="*80)
    print("Trying to get execution history...")
    print("="*80)
    
    # Cloud Scheduler doesn't expose execution history via API easily
    # But we can check the job's status
    
    print("\nFull scheduler config:")
    print(json.dumps(sched, indent=2))
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("MANUAL CHECK REQUIRED")
print("="*80)
print("\nThe scheduler API doesn't expose detailed error messages easily.")
print("\nPlease do this:")
print("1. Go to Cloud Scheduler:")
print(f"   https://console.cloud.google.com/cloudscheduler?project={PROJECT_ID}")
print("\n2. Click on 'inventory-updater-schedule'")
print("\n3. Look for:")
print("   - 'VIEW LOGS' button (click it)")
print("   - Or 'Execution history' section")
print("   - Or click on the failed execution")
print("\n4. Copy the EXACT error message you see")
print("   (Look for things like 'UNAUTHENTICATED', 'PERMISSION_DENIED', etc.)")
print("\n5. Share that exact error message with me")
print("\nOnce I have the exact error, I can fix it properly.")
print("="*80)
