#!/usr/bin/env python3
"""Check current scheduler status and recent errors"""

import os
import sys
from datetime import datetime, timedelta

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
print("CHECKING CURRENT STATUS")
print("="*80)

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)
run = build('run', 'v2', http=authorized_http)

# Check scheduler
print("\n[1/3] Checking Cloud Scheduler...")
scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

try:
    sched = scheduler.projects().locations().jobs().get(name=scheduler_name).execute()
    
    print(f"  State: {sched.get('state')}")
    print(f"  Schedule: {sched.get('schedule')}")
    
    status = sched.get('status', {})
    last_attempt = status.get('lastAttemptTime', 'Never')
    next_run = status.get('scheduleTime', 'Not scheduled')
    
    print(f"  Last attempt: {last_attempt}")
    print(f"  Next run: {next_run}")
    
    # Check last attempt result
    last_result = status.get('lastAttemptResult', {})
    if last_result:
        code = last_result.get('code')
        message = last_result.get('message', '')
        http_response = last_result.get('httpTargetResponse', {})
        http_status = http_response.get('statusCode')
        
        print(f"\n  Last Attempt Result:")
        print(f"    Code: {code}")
        if http_status:
            print(f"    HTTP Status: {http_status}")
        print(f"    Message: {message}")
        
        if code != 0:
            print(f"\n  ERROR DETAILS:")
            if code == 16:  # UNAUTHENTICATED
                print(f"    UNAUTHENTICATED - Authentication failed")
                print(f"    Possible causes:")
                print(f"      1. Service Account Token Creator role not granted yet")
                print(f"      2. Role granted but not propagated (wait 1-2 minutes)")
                print(f"      3. OIDC token configuration issue")
            elif http_status == 401:
                print(f"    HTTP 401 Unauthorized")
                print(f"    Service account cannot authenticate")
            elif http_status == 403:
                print(f"    HTTP 403 Forbidden")
                print(f"    Service account lacks permission")
            else:
                print(f"    Error code: {code}, HTTP: {http_status}")
    else:
        print(f"  No last attempt result (scheduler hasn't run yet)")
        
    # Check HTTP target config
    http_target = sched.get('httpTarget', {})
    uri = http_target.get('uri', '')
    oidc_token = http_target.get('oidcToken', {})
    sa_email = oidc_token.get('serviceAccountEmail', '')
    
    print(f"\n  Configuration:")
    print(f"    URI: {uri}")
    print(f"    Service Account: {sa_email}")
    
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Check Cloud Run Job executions
print("\n[2/3] Checking Cloud Run Job executions...")
job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'

try:
    executions = run.projects().locations().jobs().executions().list(
        parent=job_name,
        pageSize=5
    ).execute()
    
    exec_list = executions.get('executions', [])
    
    if exec_list:
        print(f"  Found {len(exec_list)} recent execution(s):")
        for i, exec_item in enumerate(exec_list[:5], 1):
            create_time = exec_item.get('createTime', 'N/A')
            conditions = exec_item.get('status', {}).get('conditions', [])
            status = 'Unknown'
            for condition in conditions:
                cond_type = condition.get('type', '')
                if cond_type in ['Completed', 'Ready', 'Failed']:
                    status = cond_type
                    break
            
            print(f"    {i}. {status} at {create_time}")
    else:
        print("  No executions found")
        
except Exception as e:
    print(f"  ERROR: {e}")

# Check service account roles
print("\n[3/3] Checking service account roles...")
sa_email = "703996360436-compute@developer.gserviceaccount.com"

print(f"  Service Account: {sa_email}")
print(f"  Required roles:")
print(f"    - Cloud Run Invoker (to invoke the job)")
print(f"    - Service Account Token Creator (to generate OIDC tokens)")
print(f"\n  Note: Check IAM & Admin to verify both roles are granted")
print(f"  https://console.cloud.google.com/iam-admin/iam?project={PROJECT_ID}")

print("\n" + "="*80)
print("TROUBLESHOOTING")
print("="*80)
print("\nIf still getting UNAUTHENTICATED:")
print("  1. Verify Service Account Token Creator role is granted")
print("  2. Wait 1-2 minutes for role propagation")
print("  3. Try manually triggering scheduler:")
print("     - Go to Cloud Scheduler")
print("     - Click 'inventory-updater-schedule'")
print("     - Click 'RUN NOW' or 'TEST' button")
print("  4. Check Cloud Logging for detailed error:")
print("     https://console.cloud.google.com/logs/query?project={PROJECT_ID}")
print("     Filter: resource.type='cloud_scheduler_job'")
