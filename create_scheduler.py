#!/usr/bin/env python3
"""Create Cloud Scheduler to run the job every 5 minutes"""

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
print("CREATING CLOUD SCHEDULER")
print("="*80)
print(f"\nJob: {JOB_NAME}")
print(f"Schedule: Every 5 minutes (*/5 * * * *)")
print(f"Region: {REGION}\n")

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)

# Create scheduler
job_uri = f"https://{REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{PROJECT_ID}/jobs/{JOB_NAME}:run"

scheduler_body = {
    'name': f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule',
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

parent = f'projects/{PROJECT_ID}/locations/{REGION}'

try:
    result = scheduler.projects().locations().jobs().create(
        parent=parent,
        body=scheduler_body
    ).execute()
    print("OK: Cloud Scheduler created!")
    print(f"\nSchedule: Runs every 5 minutes")
    print(f"View: https://console.cloud.google.com/cloudscheduler?project={PROJECT_ID}")
except Exception as e:
    if 'already exists' in str(e).lower():
        print("OK: Cloud Scheduler already exists!")
    else:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

print("\n" + "="*80)
print("SETUP COMPLETE!")
print("="*80)
print(f"\nOK: Cloud Run Job: {JOB_NAME}")
print(f"OK: Cloud Scheduler: Runs every 5 minutes")
print(f"\nYour inventory updater will now run automatically every 5 minutes!")
print(f"\nView jobs: https://console.cloud.google.com/run/jobs?project={PROJECT_ID}")
print(f"View scheduler: https://console.cloud.google.com/cloudscheduler?project={PROJECT_ID}")
