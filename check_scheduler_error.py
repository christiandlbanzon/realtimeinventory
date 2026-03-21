#!/usr/bin/env python3
"""Check why scheduler is failing"""

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
print("CHECKING SCHEDULER ERROR")
print("="*80)

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)

# Get scheduler details
scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

print(f"\n[1/3] Getting scheduler status...")
try:
    sched = scheduler.projects().locations().jobs().get(name=scheduler_name).execute()
    
    print(f"  State: {sched.get('state')}")
    print(f"  Schedule: {sched.get('schedule')}")
    print(f"  Timezone: {sched.get('timeZone')}")
    
    # Check status and last attempt
    status = sched.get('status', {})
    last_attempt = status.get('lastAttemptTime', 'Never')
    next_run = status.get('scheduleTime', 'Not scheduled')
    
    print(f"\n  Last attempt: {last_attempt}")
    print(f"  Next run: {next_run}")
    
    # Check last attempt result - THIS IS THE KEY
    last_result = status.get('lastAttemptResult', {})
    if last_result:
        code = last_result.get('code')
        message = last_result.get('message', '')
        http_status = last_result.get('httpTargetResponse', {}).get('statusCode')
        
        print(f"\n  Last Attempt Result:")
        print(f"    Code: {code}")
        if http_status:
            print(f"    HTTP Status: {http_status}")
        print(f"    Message: {message}")
        
        if code != 0:
            print(f"\n  ERROR DETAILS:")
            if code == 7:  # PERMISSION_DENIED
                print(f"    Permission denied - service account needs Cloud Run Invoker role")
            elif code == 3:  # INVALID_ARGUMENT
                print(f"    Invalid argument - check the target URL")
            elif code == 13:  # INTERNAL
                print(f"    Internal error - Google Cloud issue")
            elif http_status == 403:
                print(f"    HTTP 403 Forbidden - permission issue")
            elif http_status == 404:
                print(f"    HTTP 404 Not Found - job doesn't exist or URL is wrong")
            elif http_status == 401:
                print(f"    HTTP 401 Unauthorized - authentication issue")
            else:
                print(f"    Unknown error code: {code}")
    else:
        print(f"\n  No last attempt result found")
        
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Check HTTP target configuration
print(f"\n[2/3] Checking HTTP target configuration...")
try:
    http_target = sched.get('httpTarget', {})
    uri = http_target.get('uri', 'N/A')
    method = http_target.get('httpMethod', 'N/A')
    oidc_token = http_target.get('oidcToken', {})
    sa_email = oidc_token.get('serviceAccountEmail', 'N/A')
    
    print(f"  URI: {uri}")
    print(f"  Method: {method}")
    print(f"  Service Account: {sa_email}")
    
    # Verify the URI is correct
    expected_uri = f"https://{REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{PROJECT_ID}/jobs/{JOB_NAME}:run"
    if uri == expected_uri:
        print(f"  OK: URI is correct")
    else:
        print(f"  WARNING: URI might be incorrect")
        print(f"    Expected: {expected_uri}")
        print(f"    Actual: {uri}")
        
except Exception as e:
    print(f"  ERROR: {e}")

# Check if Cloud Run Job exists
print(f"\n[3/3] Verifying Cloud Run Job exists...")
run = build('run', 'v2', http=authorized_http)
job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'

try:
    job = run.projects().locations().jobs().get(name=job_name).execute()
    print(f"  Job exists: {job.get('name')}")
    print(f"  State: {job.get('state', 'ACTIVE')}")
    print(f"  OK: Cloud Run Job exists and is active")
except Exception as e:
    print(f"  ERROR: Cloud Run Job doesn't exist or can't be accessed")
    print(f"    {e}")

print("\n" + "="*80)
print("DIAGNOSIS")
print("="*80)
print("\nCommon causes of scheduler failures:")
print("  1. Permission denied (403) - service account needs Cloud Run Invoker role")
print("  2. Job not found (404) - Cloud Run Job doesn't exist")
print("  3. Authentication failed (401) - OIDC token issue")
print("  4. Wrong URL - scheduler pointing to wrong endpoint")
print("\nCheck the 'Last Attempt Result' above for the specific error code.")
print("\nTo view detailed logs:")
print(f"  https://console.cloud.google.com/cloudscheduler?project={PROJECT_ID}")
print("  Click on 'inventory-updater-schedule' → View logs")
