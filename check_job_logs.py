#!/usr/bin/env python3
"""Check Cloud Run Job execution logs to see what happened"""

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
print("CHECKING CLOUD RUN JOB LOGS")
print("="*80)

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/logging.read']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
run = build('run', 'v2', http=authorized_http)
logging = build('logging', 'v2', http=authorized_http)

# Get recent executions
job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'

print(f"\n[1/2] Getting recent executions...")
try:
    executions = run.projects().locations().jobs().executions().list(
        parent=job_name,
        pageSize=5
    ).execute()
    
    exec_list = executions.get('executions', [])
    
    if exec_list:
        print(f"  Found {len(exec_list)} execution(s)\n")
        
        for i, exec_item in enumerate(exec_list[:3], 1):
            exec_name = exec_item.get('name', 'N/A')
            create_time = exec_item.get('createTime', 'N/A')
            completion_time = exec_item.get('completionTime', 'N/A')
            
            conditions = exec_item.get('status', {}).get('conditions', [])
            status = 'Unknown'
            for condition in conditions:
                cond_type = condition.get('type', '')
                if cond_type in ['Completed', 'Ready', 'Failed']:
                    status = cond_type
                    break
            
            print(f"  Execution {i}:")
            print(f"    Status: {status}")
            print(f"    Started: {create_time}")
            if completion_time:
                print(f"    Completed: {completion_time}")
            print()
    else:
        print("  No executions found")
        
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Try to get logs using Cloud Logging API
print(f"[2/2] Getting logs from Cloud Logging...")
print("  (This shows what the job actually did)\n")

# Query logs for the job execution
log_filter = f'''
resource.type="cloud_run_job"
resource.labels.job_name="{JOB_NAME}"
resource.labels.location="{REGION}"
timestamp>="{datetime.now() - timedelta(hours=2)}"
'''

try:
    # Use the correct API method
    entries = logging.entries().list(
        resourceNames=[f'projects/{PROJECT_ID}'],
        filter=log_filter,
        pageSize=100,
        orderBy='timestamp desc'
    ).execute()
    
    log_entries = entries.get('entries', [])
    
    if log_entries:
        print(f"  Found {len(log_entries)} log entries\n")
        print("="*80)
        print("RECENT LOG OUTPUT")
        print("="*80)
        print()
        
        # Show important log messages
        important_keywords = ['error', 'success', 'completed', 'updated', 'sheet', 'tab', '2-2', 'february', 'clover', 'sales']
        
        shown_count = 0
        for entry in log_entries:
            if shown_count >= 50:  # Limit output
                break
                
            timestamp = entry.get('timestamp', '')
            severity = entry.get('severity', 'INFO')
            
            # Get message
            text_payload = entry.get('textPayload', '')
            json_payload = entry.get('jsonPayload', {})
            
            if json_payload:
                message = json_payload.get('message', '')
                if not message:
                    message = json_payload.get('textPayload', str(json_payload))
            else:
                message = text_payload
            
            if message:
                # Format timestamp
                if timestamp:
                    ts_str = timestamp[:19].replace('T', ' ')
                else:
                    ts_str = 'N/A'
                
                # Show all entries (they're already filtered and sorted)
                print(f"[{ts_str}] [{severity}] {message}")
                shown_count += 1
        
        print()
        print("="*80)
        
        # Summary
        error_count = sum(1 for e in log_entries if e.get('severity') == 'ERROR')
        warning_count = sum(1 for e in log_entries if e.get('severity') == 'WARNING')
        
        print(f"\nSummary:")
        print(f"  Total log entries: {len(log_entries)}")
        print(f"  Errors: {error_count}")
        print(f"  Warnings: {warning_count}")
        
        if error_count > 0:
            print(f"\n  WARNING: Found {error_count} error(s) - check logs above")
        else:
            print(f"\n  No errors found in logs")
            
    else:
        print("  No log entries found")
        print("\n  This could mean:")
        print("    1. Logs haven't been written yet")
        print("    2. Need to check Cloud Logging console directly")
        print("    3. The job might not have run yet")
        
except Exception as e:
    print(f"  ERROR retrieving logs: {e}")
    import traceback
    traceback.print_exc()
    print("\n  You can view logs directly in Console:")
    print(f"    https://console.cloud.google.com/logs/query?project={PROJECT_ID}")

print("\n" + "="*80)
print("NEXT STEPS")
print("="*80)
print(f"\n1. Check Cloud Run Job execution logs:")
print(f"   https://console.cloud.google.com/run/jobs/{JOB_NAME}/executions?project={PROJECT_ID}&location={REGION}")
print(f"\n2. Check Cloud Logging:")
print(f"   https://console.cloud.google.com/logs/query?project={PROJECT_ID}")
print(f"   Filter: resource.type=\"cloud_run_job\" AND resource.labels.job_name=\"{JOB_NAME}\"")
print(f"\n3. Manually trigger the job to test:")
print(f"   python trigger_job.py")
