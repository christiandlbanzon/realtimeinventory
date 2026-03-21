#!/usr/bin/env python3
"""Check Cloud Run Job execution logs and status"""

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
print("CHECKING JOB EXECUTION STATUS")
print("="*80)

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
run = build('run', 'v2', http=authorized_http)
logging = build('logging', 'v2', http=authorized_http)

# Get job
job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'

print(f"\n[1/3] Getting job details...")
try:
    job = run.projects().locations().jobs().get(name=job_name).execute()
    print(f"  Job: {JOB_NAME}")
    print(f"  State: {job.get('state', 'ACTIVE')}")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# List recent executions
print(f"\n[2/3] Getting recent executions...")
try:
    executions = run.projects().locations().jobs().executions().list(
        parent=job_name,
        pageSize=5
    ).execute()
    
    exec_list = executions.get('executions', [])
    
    if exec_list:
        print(f"  Found {len(exec_list)} recent execution(s):\n")
        
        for i, exec_item in enumerate(exec_list[:5], 1):
            exec_name = exec_item.get('name', 'N/A')
            create_time = exec_item.get('createTime', 'N/A')
            conditions = exec_item.get('status', {}).get('conditions', [])
            
            # Get execution status
            status = 'Unknown'
            reason = ''
            message = ''
            
            for condition in conditions:
                cond_type = condition.get('type', '')
                if cond_type in ['Completed', 'Ready', 'Failed']:
                    status = cond_type
                    reason = condition.get('reason', '')
                    message = condition.get('message', '')
                    break
            
            print(f"  Execution {i}:")
            print(f"    Status: {status}")
            print(f"    Started: {create_time}")
            
            if reason:
                print(f"    Reason: {reason}")
            if message:
                print(f"    Message: {message}")
            
            # Get completion time
            completion_time = exec_item.get('completionTime')
            if completion_time:
                print(f"    Completed: {completion_time}")
            
            # Get logs for this execution
            exec_id = exec_name.split('/')[-1]
            print(f"\n    Getting logs for this execution...")
            
            # Query logs
            log_filter = f'''
resource.type="cloud_run_job"
resource.labels.job_name="{JOB_NAME}"
resource.labels.location="{REGION}"
timestamp>="{create_time}"
'''
            
            try:
                logs = logging.entries().list(
                    projectIds=[PROJECT_ID],
                    filter=log_filter,
                    pageSize=50,
                    orderBy='timestamp desc'
                ).execute()
                
                log_entries = logs.get('entries', [])
                if log_entries:
                    print(f"    Found {len(log_entries)} log entries")
                    print(f"\n    Recent log output:")
                    print(f"    {'-'*70}")
                    
                    # Show last 20 log entries
                    for entry in log_entries[:20]:
                        timestamp = entry.get('timestamp', '')
                        text_payload = entry.get('textPayload', '')
                        json_payload = entry.get('jsonPayload', {})
                        
                        if json_payload:
                            message = json_payload.get('message', str(json_payload))
                        else:
                            message = text_payload
                        
                        if message:
                            # Truncate long messages
                            if len(message) > 200:
                                message = message[:200] + "..."
                            print(f"    [{timestamp}] {message}")
                    
                    print(f"    {'-'*70}")
                else:
                    print(f"    No log entries found")
                    
            except Exception as e:
                print(f"    Could not retrieve logs: {e}")
            
            print()
            
    else:
        print("  No executions found")
        
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Check scheduler status
print(f"[3/3] Checking scheduler status...")
scheduler = build('cloudscheduler', 'v1', http=authorized_http)
scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

try:
    scheduler_job = scheduler.projects().locations().jobs().get(name=scheduler_name).execute()
    status = scheduler_job.get('status', {})
    last_attempt = status.get('lastAttemptTime', 'Never')
    next_run = status.get('scheduleTime', 'Not scheduled')
    
    print(f"  Scheduler: {scheduler_job.get('state', 'UNKNOWN')}")
    print(f"  Last attempt: {last_attempt}")
    print(f"  Next run: {next_run}")
    
    # Check last attempt result
    last_attempt_result = status.get('lastAttemptResult', {})
    if last_attempt_result:
        code = last_attempt_result.get('code')
        if code == 0:
            print(f"  Last attempt: SUCCESS")
        else:
            print(f"  Last attempt: FAILED (code {code})")
            print(f"    Message: {last_attempt_result.get('message', 'N/A')}")
    
except Exception as e:
    print(f"  Could not check scheduler: {e}")

print("\n" + "="*80)
print("VIEW IN CONSOLE")
print("="*80)
print(f"\nView executions:")
print(f"  https://console.cloud.google.com/run/jobs/{JOB_NAME}/executions?project={PROJECT_ID}&location={REGION}")
print(f"\nView logs:")
print(f"  https://console.cloud.google.com/logs/query?project={PROJECT_ID}")
print(f"\nView scheduler:")
print(f"  https://console.cloud.google.com/cloudscheduler?project={PROJECT_ID}")
