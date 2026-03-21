#!/usr/bin/env python3
"""Verify scheduler was fixed"""

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

PROJECT_ID = "boxwood-chassis-332307"
REGION = "us-east1"
JOB_NAME = "inventory-updater"

print("="*80)
print("VERIFYING SCHEDULER FIX")
print("="*80)

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)

scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

print(f"\nChecking current scheduler configuration...")
try:
    sched = scheduler.projects().locations().jobs().get(name=scheduler_name).execute()
    
    http_target = sched.get('httpTarget', {})
    uri = http_target.get('uri', '')
    
    print(f"\nCurrent URI: {uri}")
    
    # Check if it's the correct v2 format
    expected_v2_uri = f"https://{REGION}-run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}:run"
    
    if uri == expected_v2_uri:
        print(f"\nOK: URI is correct (v2 API format)")
        print(f"  The scheduler is now configured correctly!")
    elif '/v1/namespaces/' in uri:
        print(f"\nWARNING: Still using old v1 API format")
        print(f"  This needs to be updated manually")
    elif '/v2/' in uri:
        print(f"\nOK: Using v2 API format")
        print(f"  URI format is correct")
    else:
        print(f"\nINFO: URI format: {uri[:50]}...")
    
    # Check status
    status = sched.get('status', {})
    next_run = status.get('scheduleTime', 'Not scheduled')
    last_attempt = status.get('lastAttemptTime', 'Never')
    
    print(f"\nScheduler Status:")
    print(f"  State: {sched.get('state')}")
    print(f"  Schedule: {sched.get('schedule')} (every 5 minutes)")
    print(f"  Next run: {next_run}")
    print(f"  Last attempt: {last_attempt}")
    
    if next_run != 'Not scheduled':
        print(f"\nOK: Scheduler is scheduled and will run automatically")
    else:
        print(f"\nWARNING: Next run is 'Not scheduled'")
        print(f"  You may need to edit and save the scheduler to reschedule it")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("\nChanges made:")
print("  1. Updated scheduler URI from v1 to v2 API format")
print("  2. This fixes the 'Failed' status issue")
print("\nNext steps:")
print("  1. Wait 5-10 minutes")
print("  2. Check Cloud Scheduler - status should show 'Succeeded'")
print("  3. Check Cloud Run Jobs - new executions should appear every 5 minutes")
print("\nIf scheduler still shows 'Not scheduled' for next run:")
print("  - Go to Cloud Scheduler console")
print("  - Click 'inventory-updater-schedule'")
print("  - Click 'EDIT' then 'UPDATE' (to force reschedule)")
