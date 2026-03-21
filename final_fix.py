#!/usr/bin/env python3
"""Final fix - remove audience and try different approach"""

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
print("FINAL FIX ATTEMPT")
print("="*80)
print("\nThe job has 0 IAM bindings - permission wasn't granted on the resource.")
print("Let's try a different approach.")
print()

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)

scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'
job_uri = f"https://{REGION}-run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}:run"

# Remove audience completely
scheduler_body = {
    'schedule': '*/5 * * * *',
    'timeZone': 'America/Puerto_Rico',
    'httpTarget': {
        'uri': job_uri,
        'httpMethod': 'POST',
        'oidcToken': {
            'serviceAccountEmail': SA_EMAIL
            # NO audience - let Cloud Scheduler handle it
        }
    }
}

try:
    print("Updating scheduler (removing audience)...")
    updated = scheduler.projects().locations().jobs().patch(
        name=scheduler_name,
        body=scheduler_body
    ).execute()
    print("  OK: Scheduler updated")
    
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "="*80)
print("CRITICAL: Grant Permission WITHOUT Condition")
print("="*80)
print("\nThe job resource has 0 IAM bindings.")
print("\nDo this:")
print("1. Go to IAM & Admin:")
print(f"   https://console.cloud.google.com/iam-admin/iam?project={PROJECT_ID}")
print("\n2. Find: scheduler-invoker@boxwood-chassis-332307.iam.gserviceaccount.com")
print("\n3. Make sure it has 'Cloud Run Invoker' role")
print("   WITHOUT any condition (remove condition if present)")
print("\n4. OR go to Cloud Run Jobs -> inventory-updater")
print("   Look for PERMISSIONS/IAM button/tab")
print("   Grant Cloud Run Invoker to scheduler-invoker@...")
print("   WITHOUT any condition")
print("\n5. Wait 3-5 minutes")
print("\n6. Manually trigger scheduler")
print("\nThe condition you added might be preventing it from working.")
print("Try WITHOUT the condition first.")
print("="*80)
