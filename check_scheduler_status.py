#!/usr/bin/env python3
"""Check Cloud Scheduler status and trigger manual test"""

import os
import sys
from datetime import datetime

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
print("CHECKING SCHEDULER STATUS")
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
print("\n[1/2] Checking Cloud Scheduler...")
scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

try:
    scheduler_job = scheduler.projects().locations().jobs().get(
        name=scheduler_name
    ).execute()
    
    print(f"  Name: {scheduler_job.get('name', 'N/A')}")
    print(f"  Schedule: {scheduler_job.get('schedule', 'N/A')}")
    print(f"  State: {scheduler_job.get('state', 'N/A')}")
    
    if scheduler_job.get('state') == 'ENABLED':
        print("  Status: ENABLED (will run automatically)")
        
        # Calculate next run (every 5 minutes)
        last_run = scheduler_job.get('status', {}).get('lastAttemptTime')
        if last_run:
            print(f"  Last run: {last_run}")
        else:
            print(f"  Last run: Never (will run at next scheduled time)")
        
        next_run = scheduler_job.get('scheduleTime')
        if next_run:
            print(f"  Next run: {next_run}")
    else:
        print(f"  WARNING: Scheduler is {scheduler_job.get('state')}")
        print("  It needs to be ENABLED to run automatically")
        
except Exception as e:
    print(f"  ERROR: Could not get scheduler: {e}")
    print("  Scheduler might not exist or there's a permission issue")

# Check Cloud Run Job
print("\n[2/2] Checking Cloud Run Job...")
job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'

try:
    job = run.projects().locations().jobs().get(
        name=job_name
    ).execute()
    
    print(f"  Name: {job.get('name', 'N/A')}")
    print(f"  State: {job.get('state', 'N/A')}")
    print(f"  Image: {job.get('template', {}).get('template', {}).get('containers', [{}])[0].get('image', 'N/A')}")
    
    # List recent executions
    print("\n  Recent executions:")
    try:
        executions = run.projects().locations().jobs().executions().list(
            parent=job_name,
            pageSize=5
        ).execute()
        
        exec_list = executions.get('executions', [])
        if exec_list:
            for exec_item in exec_list[:5]:
                status = exec_item.get('status', {}).get('conditions', [{}])[0].get('type', 'Unknown')
                create_time = exec_item.get('createTime', 'N/A')
                print(f"    - {status} at {create_time}")
        else:
            print("    - No executions yet")
            print("    - This is normal if the job was just created")
            print("    - Scheduler will trigger it automatically")
    except Exception as e:
        print(f"    - Could not list executions: {e}")
        
except Exception as e:
    print(f"  ERROR: Could not get job: {e}")

print("\n" + "="*80)
print("MANUAL TEST")
print("="*80)
print("\nTo test the job manually, run:")
print(f"  python trigger_job.py")
print("\nOr in Console:")
print(f"  1. Go to: https://console.cloud.google.com/run/jobs?project={PROJECT_ID}")
print(f"  2. Click 'inventory-updater'")
print(f"  3. Click 'EXECUTE' button")
