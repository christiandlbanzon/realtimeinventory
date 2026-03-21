#!/usr/bin/env python3
"""Check why scheduler isn't running every 5 minutes"""

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
print("CHECKING SCHEDULER RUN HISTORY")
print("="*80)

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
run = build('run', 'v2', http=authorized_http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)

# Check scheduler status
print("\n[1/3] Checking Cloud Scheduler...")
scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

try:
    sched = scheduler.projects().locations().jobs().get(name=scheduler_name).execute()
    
    print(f"  Name: {sched.get('name')}")
    print(f"  State: {sched.get('state')}")
    print(f"  Schedule: {sched.get('schedule')}")
    print(f"  Timezone: {sched.get('timeZone', 'UTC')}")
    
    status = sched.get('status', {})
    last_attempt = status.get('lastAttemptTime', 'Never')
    next_run = status.get('scheduleTime', 'Not scheduled')
    
    print(f"\n  Last attempt: {last_attempt}")
    print(f"  Next run: {next_run}")
    
    # Check last attempt result
    last_result = status.get('lastAttemptResult', {})
    if last_result:
        code = last_result.get('code')
        message = last_result.get('message', '')
        if code == 0:
            print(f"  Last attempt result: SUCCESS")
        else:
            print(f"  Last attempt result: FAILED (code {code})")
            print(f"    Message: {message}")
    
    if sched.get('state') != 'ENABLED':
        print(f"\n  WARNING: Scheduler is {sched.get('state')}, not ENABLED!")
        print(f"  This is why it's not running automatically.")
    
    if next_run == 'Not scheduled':
        print(f"\n  WARNING: Next run is 'Not scheduled'")
        print(f"  This means the scheduler might not be triggering automatically.")
        print(f"  Possible reasons:")
        print(f"    1. Scheduler needs to be rescheduled (edit and save)")
        print(f"    2. Permissions issue preventing scheduler from running")
        print(f"    3. Scheduler is paused or disabled")
        
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Check all executions
print("\n[2/3] Checking all executions...")
job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'

try:
    executions = run.projects().locations().jobs().executions().list(
        parent=job_name,
        pageSize=20  # Get more executions to see pattern
    ).execute()
    
    exec_list = executions.get('executions', [])
    
    if exec_list:
        print(f"  Found {len(exec_list)} execution(s):\n")
        
        # Parse times and show pattern
        exec_times = []
        for exec_item in exec_list:
            create_time = exec_item.get('createTime', '')
            if create_time:
                # Parse ISO format
                try:
                    dt = datetime.fromisoformat(create_time.replace('Z', '+00:00'))
                    exec_times.append(dt)
                except:
                    pass
        
        # Sort by time
        exec_times.sort(reverse=True)
        
        print("  Execution times (most recent first):")
        for i, dt in enumerate(exec_times[:10], 1):
            print(f"    {i}. {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        # Check time gaps
        if len(exec_times) >= 2:
            print(f"\n  Time gaps between executions:")
            for i in range(len(exec_times) - 1):
                gap = exec_times[i] - exec_times[i+1]
                minutes = gap.total_seconds() / 60
                print(f"    {exec_times[i].strftime('%H:%M')} - {exec_times[i+1].strftime('%H:%M')}: {minutes:.1f} minutes")
            
            # Check if gaps are ~5 minutes
            recent_gaps = []
            for i in range(min(3, len(exec_times) - 1)):
                gap = exec_times[i] - exec_times[i+1]
                minutes = gap.total_seconds() / 60
                recent_gaps.append(minutes)
            
            avg_gap = sum(recent_gaps) / len(recent_gaps) if recent_gaps else 0
            print(f"\n  Average gap (last 3): {avg_gap:.1f} minutes")
            
            if avg_gap > 10:
                print(f"  WARNING: Gaps are longer than 5 minutes!")
                print(f"  The scheduler might not be running every 5 minutes.")
            elif 4 <= avg_gap <= 6:
                print(f"  OK: Gaps are approximately 5 minutes (scheduler working)")
            else:
                print(f"  INFO: Gaps vary - some manual triggers may be included")
    else:
        print("  No executions found")
        
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Check if scheduler can actually trigger
print("\n[3/3] Checking scheduler permissions...")
print("  The scheduler needs permission to invoke the Cloud Run Job.")
print("  Service account: 703996360436-compute@developer.gserviceaccount.com")
print("  Required role: Cloud Run Invoker")
print("\n  If scheduler shows 'Not scheduled' for next run:")
print("  1. Go to Cloud Scheduler console")
print("  2. Click 'inventory-updater-schedule'")
print("  3. Click 'EDIT' then 'SAVE' (this reschedules it)")
print("  4. Or check permissions in Cloud Run Job → Permissions tab")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("\nIf last run was 8:33 PM and it's not running every 5 minutes:")
print("  1. Check if scheduler is ENABLED")
print("  2. Check if 'Next run' shows a future time")
print("  3. If 'Not scheduled', edit and save the scheduler to reschedule")
print("  4. Verify permissions are correct")
