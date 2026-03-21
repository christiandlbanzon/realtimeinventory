#!/usr/bin/env python3
"""Fix scheduler to actually run automatically"""

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
print("FIXING SCHEDULER TO RUN AUTOMATICALLY")
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

# Get current scheduler config
scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

print("\n[1/3] Getting current scheduler configuration...")
try:
    current = scheduler.projects().locations().jobs().get(name=scheduler_name).execute()
    print(f"  Current state: {current.get('state')}")
    print(f"  Schedule: {current.get('schedule')}")
    print(f"  Timezone: {current.get('timeZone')}")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# Update scheduler (this forces it to reschedule)
print("\n[2/3] Updating scheduler to force reschedule...")
job_uri = f"https://{REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{PROJECT_ID}/jobs/{JOB_NAME}:run"

scheduler_body = {
    'schedule': '*/5 * * * *',  # Every 5 minutes
    'timeZone': 'America/Puerto_Rico',
    'httpTarget': {
        'uri': job_uri,
        'httpMethod': 'POST',
        'oidcToken': {
            'serviceAccountEmail': '703996360436-compute@developer.gserviceaccount.com'
        }
    }
}

try:
    # Update the scheduler (this will reschedule it)
    updated = scheduler.projects().locations().jobs().patch(
        name=scheduler_name,
        body=scheduler_body
    ).execute()
    
    print("  OK: Scheduler updated")
    
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verify it's scheduled
print("\n[3/3] Verifying scheduler is scheduled...")
try:
    updated_sched = scheduler.projects().locations().jobs().get(name=scheduler_name).execute()
    status = updated_sched.get('status', {})
    next_run = status.get('scheduleTime', 'Not scheduled')
    
    print(f"  State: {updated_sched.get('state')}")
    print(f"  Next run: {next_run}")
    
    if next_run != 'Not scheduled':
        print("\n  OK: Scheduler is now scheduled!")
        print(f"  It will run automatically every 5 minutes")
    else:
        print("\n  WARNING: Still showing 'Not scheduled'")
        print("  This might be a display delay - check again in a minute")
        print("  Or you may need to fix permissions manually")
        
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "="*80)
print("SCHEDULER FIXED")
print("="*80)
print("\nThe scheduler should now run automatically every 5 minutes.")
print("\nTo verify:")
print("  1. Wait 5 minutes")
print("  2. Check Cloud Run Jobs executions")
print("  3. You should see new executions appearing every 5 minutes")
print("\nView scheduler:")
print(f"  https://console.cloud.google.com/cloudscheduler?project={PROJECT_ID}")
