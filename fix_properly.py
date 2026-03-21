#!/usr/bin/env python3
"""Fix this properly using Cloud Run Job's Triggers tab"""

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
SA_EMAIL = "scheduler-invoker@boxwood-chassis-332307.iam.gserviceaccount.com"

print("="*80)
print("FIXING THIS PROPERLY")
print("="*80)
print("\nAccording to Google Cloud documentation:")
print("Cloud Run Jobs have a 'TRIGGERS' tab that creates scheduler triggers")
print("WITH proper authentication automatically.")
print("\nWe've been creating a separate Cloud Scheduler job, which is wrong!")
print()

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)

# Delete the existing separate scheduler job
scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

print("[1/2] Deleting the incorrectly created Cloud Scheduler job...")
try:
    scheduler.projects().locations().jobs().delete(name=scheduler_name).execute()
    print(f"  OK: Deleted {JOB_NAME}-schedule")
except Exception as e:
    if '404' in str(e) or 'not found' in str(e).lower():
        print(f"  OK: Scheduler job doesn't exist (already deleted or never created)")
    else:
        print(f"  ERROR: {e}")
        print(f"  You may need to delete it manually")

print("\n[2/2] Create trigger properly via Console:")
print("="*80)
print("\n1. Go to Cloud Run Jobs:")
print(f"   https://console.cloud.google.com/run/jobs?project={PROJECT_ID}")
print(f"\n2. Click on '{JOB_NAME}'")
print("\n3. Click the 'TRIGGERS' tab (at the top, next to History, Observability, etc.)")
print("\n4. Click 'ADD SCHEDULER TRIGGER' or 'CREATE TRIGGER'")
print("\n5. Fill in:")
print(f"   - Name: {JOB_NAME}-schedule")
print(f"   - Region: {REGION}")
print(f"   - Schedule: */5 * * * *")
print(f"   - Timezone: America/Puerto_Rico")
print(f"   - Service Account: {SA_EMAIL}")
print("\n6. Click 'CREATE'")
print("\nThis creates the trigger WITH proper authentication!")
print("The Triggers tab handles everything automatically.")
print("="*80)
