#!/usr/bin/env python3
"""Diagnose why scheduler is failing to trigger the job"""

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
logging_api = build('logging', 'v2', http=authorized_http)

print("="*80)
print("DIAGNOSING SCHEDULER FAILURE")
print("="*80)

# Check scheduler config
scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

try:
    print("\n[1/4] Checking scheduler configuration...")
    sched = scheduler.projects().locations().jobs().get(name=scheduler_name).execute()
    
    http_target = sched.get('httpTarget', {})
    oidc_token = http_target.get('oidcToken', {})
    uri = http_target.get('uri', '')
    method = http_target.get('httpMethod', '')
    
    print(f"  URI: {uri}")
    print(f"  Method: {method}")
    print(f"  Service Account: {oidc_token.get('serviceAccountEmail', 'N/A')}")
    print(f"  Audience: {oidc_token.get('audience', 'N/A')}")
    
    # Check if URI is correct
    expected_uri = f"https://{REGION}-run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}:run"
    if uri != expected_uri:
        print(f"\n  WARNING: URI mismatch!")
        print(f"  Expected: {expected_uri}")
        print(f"  Actual: {uri}")
    else:
        print(f"  OK: URI is correct")
    
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Check Cloud Run Job exists and is accessible
try:
    print("\n[2/4] Checking Cloud Run Job...")
    job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'
    job = run.projects().locations().jobs().get(name=job_name).execute()
    print(f"  Job exists: {job.get('name', 'N/A')}")
    print(f"  State: {job.get('state', 'N/A')}")
    
except Exception as e:
    print(f"  ERROR: {e}")

# Try to manually trigger the job to see if it works
try:
    print("\n[3/4] Testing manual job trigger...")
    job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'
    
    print("  Attempting to run job manually...")
    operation = run.projects().locations().jobs().run(
        name=job_name,
        body={}
    ).execute()
    
    print(f"  OK: Job triggered successfully")
    print(f"  Operation: {operation.get('name', 'N/A')}")
    
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Check recent scheduler logs
try:
    print("\n[4/4] Checking recent scheduler logs...")
    print("  Note: Detailed logs require Logging API access")
    print("  Check manually at:")
    print(f"  https://console.cloud.google.com/logs/query?project={PROJECT_ID}")
    print(f"  Filter: resource.type=\"cloud_scheduler_job\"")
    print(f"          resource.labels.job_id=\"{JOB_NAME}-schedule\"")
    
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "="*80)
print("TROUBLESHOOTING STEPS")
print("="*80)
print("\n1. Check scheduler logs for the exact error:")
print(f"   https://console.cloud.google.com/logs/query?project={PROJECT_ID}")
print("\n2. Verify service account has correct roles:")
print(f"   https://console.cloud.google.com/iam-admin/iam?project={PROJECT_ID}")
print(f"   Look for: scheduler-invoker@boxwood-chassis-332307.iam.gserviceaccount.com")
print("\n3. Try manually triggering scheduler:")
print(f"   https://console.cloud.google.com/cloudscheduler?project={PROJECT_ID}")
print("   Click 'RUN NOW' on the scheduler job")
print("\n4. Check Cloud Run Job IAM permissions:")
print(f"   The service account needs 'Cloud Run Invoker' on the JOB itself")
print("="*80)
