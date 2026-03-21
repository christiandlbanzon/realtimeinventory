#!/usr/bin/env python3
"""Check recent scheduler execution logs"""

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

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)
run = build('run', 'v2', http=authorized_http)

print("="*80)
print("RECENT SCHEDULER EXECUTIONS")
print("="*80)

# Check scheduler status
scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

try:
    sched = scheduler.projects().locations().jobs().get(name=scheduler_name).execute()
    print(f"\n[SCHEDULER STATUS]")
    print(f"  State: {sched.get('state', 'N/A')}")
    print(f"  Schedule: {sched.get('schedule', 'N/A')}")
    
    # Get recent job executions
    print(f"\n[CLOUD RUN JOB EXECUTIONS]")
    job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'
    
    executions = run.projects().locations().jobs().executions().list(
        parent=job_name,
        pageSize=10
    ).execute()
    
    execs = executions.get('executions', [])
    
    if execs:
        print(f"\n  Found {len(execs)} recent executions:\n")
        for i, exec_item in enumerate(execs[:10], 1):
            name = exec_item.get('name', 'N/A')
            state = exec_item.get('state', 'N/A')
            create_time = exec_item.get('createTime', 'N/A')
            completion_time = exec_item.get('completionTime', 'N/A')
            
            # Parse timestamps
            try:
                if create_time:
                    create_dt = datetime.fromisoformat(create_time.replace('Z', '+00:00'))
                    create_str = create_dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    create_str = 'N/A'
                    
                if completion_time:
                    comp_dt = datetime.fromisoformat(completion_time.replace('Z', '+00:00'))
                    comp_str = comp_dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    comp_str = 'Not completed'
            except:
                create_str = create_time
                comp_str = completion_time
            
            status_icon = "SUCCESS" if state == "SUCCEEDED" else ("FAILED" if state == "FAILED" else state)
            
            print(f"  Execution {i}:")
            print(f"    State: {status_icon}")
            print(f"    Started: {create_str}")
            if completion_time:
                print(f"    Completed: {comp_str}")
            print()
    else:
        print("  No executions found")
    
    # Check if there are recent failures
    recent_failures = [e for e in execs if e.get('state') == 'FAILED']
    if recent_failures:
        print(f"\n  WARNING: Found {len(recent_failures)} failed execution(s)")
        print(f"  Check logs for details")
    else:
        print(f"\n  All recent executions appear successful!")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("To view detailed logs:")
print(f"  https://console.cloud.google.com/logs/query?project={PROJECT_ID}")
print("="*80)
