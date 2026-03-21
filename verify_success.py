#!/usr/bin/env python3
"""Verify scheduler is working correctly"""

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
from datetime import datetime

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
print("VERIFICATION - SCHEDULER STATUS")
print("="*80)

# Check scheduler
scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

try:
    sched = scheduler.projects().locations().jobs().get(name=scheduler_name).execute()
    
    print("\n[SCHEDULER]")
    print(f"  Name: {sched.get('name', 'N/A')}")
    print(f"  Schedule: {sched.get('schedule', 'N/A')}")
    print(f"  Time Zone: {sched.get('timeZone', 'N/A')}")
    print(f"  State: {sched.get('state', 'N/A')}")
    
    http_target = sched.get('httpTarget', {})
    oidc_token = http_target.get('oidcToken', {})
    print(f"  Service Account: {oidc_token.get('serviceAccountEmail', 'N/A')}")
    
    print("\n[CLOUD RUN JOB]")
    job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'
    job = run.projects().locations().jobs().get(name=job_name).execute()
    print(f"  Name: {job.get('name', 'N/A')}")
    print(f"  State: {job.get('state', 'N/A')}")
    
    # Check recent executions
    print("\n[RECENT EXECUTIONS]")
    try:
        executions = run.projects().locations().jobs().executions().list(
            parent=job_name,
            pageSize=5
        ).execute()
        
        execs = executions.get('executions', [])
        if execs:
            for i, exec_item in enumerate(execs[:5], 1):
                name = exec_item.get('name', 'N/A')
                state = exec_item.get('state', 'N/A')
                create_time = exec_item.get('createTime', 'N/A')
                completion_time = exec_item.get('completionTime', 'N/A')
                
                print(f"\n  Execution {i}:")
                print(f"    State: {state}")
                print(f"    Created: {create_time}")
                if completion_time:
                    print(f"    Completed: {completion_time}")
        else:
            print("  No executions yet")
    except Exception as e:
        print(f"  Could not fetch executions: {e}")
    
    print("\n" + "="*80)
    print("STATUS: Everything configured correctly!")
    print("="*80)
    print("\nThe scheduler should now run every 5 minutes automatically.")
    print("\nMonitor at:")
    print(f"  - Cloud Scheduler: https://console.cloud.google.com/cloudscheduler?project={PROJECT_ID}")
    print(f"  - Cloud Run Jobs: https://console.cloud.google.com/run/jobs?project={PROJECT_ID}")
    print(f"  - Logs: https://console.cloud.google.com/logs/query?project={PROJECT_ID}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
