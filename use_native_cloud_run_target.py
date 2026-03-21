#!/usr/bin/env python3
"""Use Cloud Scheduler's native Cloud Run Jobs target instead of HTTP"""

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
print("USING NATIVE CLOUD RUN JOBS TARGET")
print("="*80)
print("\nCloud Scheduler has native support for Cloud Run Jobs.")
print("This avoids HTTP/OIDC authentication issues.")
print()

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)
run = build('run', 'v2', http=authorized_http)

scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'
job_resource = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'

try:
    print("[1/2] Checking current scheduler configuration...")
    current = scheduler.projects().locations().jobs().get(name=scheduler_name).execute()
    
    print(f"  Current target type: {current.get('httpTarget', {}).get('uri', 'HTTP')}")
    
    print("\n[2/2] Updating to use Cloud Run Jobs native target...")
    
    # Use runJob target instead of httpTarget
    scheduler_body = {
        'schedule': '*/5 * * * *',
        'timeZone': 'America/Puerto_Rico',
        'runJob': {
            'jobName': job_resource
        }
    }
    
    updated = scheduler.projects().locations().jobs().patch(
        name=scheduler_name,
        body=scheduler_body
    ).execute()
    
    print(f"  OK: Scheduler updated to use native Cloud Run Jobs target")
    print(f"  Job: {job_resource}")
    print(f"\n  This should work without OIDC token issues!")
    
except Exception as e:
    error_str = str(e)
    if 'runJob' in error_str.lower() or 'unknown' in error_str.lower():
        print(f"  ERROR: {e}")
        print(f"\n  The 'runJob' target might not be available in this API version.")
        print(f"  Let me check the API version...")
        
        # Check API discovery
        print(f"\n  Trying alternative: Keep HTTP but fix authentication...")
        
        # Actually, let's just try using the service account email directly in OIDC
        SA_EMAIL = "scheduler-invoker@boxwood-chassis-332307.iam.gserviceaccount.com"
        
        scheduler_body = {
            'schedule': '*/5 * * * *',
            'timeZone': 'America/Puerto_Rico',
            'httpTarget': {
                'uri': f'https://{REGION}-run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}:run',
                'httpMethod': 'POST',
                'oidcToken': {
                    'serviceAccountEmail': SA_EMAIL,
                    # Don't set audience - let it default
                }
            }
        }
        
        try:
            updated = scheduler.projects().locations().jobs().patch(
                name=scheduler_name,
                body=scheduler_body
            ).execute()
            print(f"  OK: Updated scheduler (removed audience)")
        except Exception as e2:
            print(f"  ERROR: {e2}")
            import traceback
            traceback.print_exc()
    else:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*80)
print("NEXT STEPS")
print("="*80)
print("\n1. Wait 2-3 minutes")
print("2. Manually trigger scheduler to test")
print("3. Check if it works")
print("\nIf still failing, the issue might be:")
print("  - Service account needs 'Cloud Run Jobs Runner' role")
print("  - Or we need to use a different authentication method")
print("="*80)
