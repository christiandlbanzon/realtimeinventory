#!/usr/bin/env python3
"""Deep diagnosis of scheduler failure"""

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
import json

PROJECT_ID = "boxwood-chassis-332307"
REGION = "us-east1"
JOB_NAME = "inventory-updater"

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/logging.read']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)
run = build('run', 'v2', http=authorized_http)

print("="*80)
print("DEEP DIAGNOSIS")
print("="*80)

# Check scheduler config in detail
scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

try:
    print("\n[1/5] Current scheduler configuration:")
    sched = scheduler.projects().locations().jobs().get(name=scheduler_name).execute()
    
    print(f"  Name: {sched.get('name')}")
    print(f"  State: {sched.get('state')}")
    print(f"  Schedule: {sched.get('schedule')}")
    print(f"  Time Zone: {sched.get('timeZone')}")
    
    http_target = sched.get('httpTarget', {})
    if http_target:
        print(f"\n  HTTP Target:")
        print(f"    URI: {http_target.get('uri')}")
        print(f"    Method: {http_target.get('httpMethod')}")
        
        oidc_token = http_target.get('oidcToken', {})
        if oidc_token:
            print(f"    OIDC Token:")
            print(f"      Service Account: {oidc_token.get('serviceAccountEmail')}")
            print(f"      Audience: {oidc_token.get('audience', 'NOT SET')}")
        else:
            print(f"    OIDC Token: NOT CONFIGURED")
    
    print(f"\n  Full config (JSON):")
    print(json.dumps(sched, indent=2))
    
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Check Cloud Run Job
try:
    print("\n[2/5] Cloud Run Job status:")
    job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'
    job = run.projects().locations().jobs().get(name=job_name).execute()
    
    print(f"  Name: {job.get('name')}")
    print(f"  State: {job.get('state')}")
    print(f"  UID: {job.get('uid')}")
    
    # Check IAM policy
    try:
        policy = run.projects().locations().jobs().getIamPolicy(resource=job_name).execute()
        bindings = policy.get('bindings', [])
        print(f"\n  IAM Bindings ({len(bindings)}):")
        for binding in bindings:
            role = binding.get('role')
            members = binding.get('members', [])
            print(f"    {role}: {members}")
    except Exception as e:
        print(f"  Could not get IAM policy: {e}")
    
except Exception as e:
    print(f"  ERROR: {e}")

# Try to manually trigger via API to see error
try:
    print("\n[3/5] Testing manual trigger via API...")
    job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'
    
    # Use the scheduler's service account credentials
    sa_creds = service_account.Credentials.from_service_account_file(
        'service-account-key.json',
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    
    # Create a new HTTP client with scheduler service account
    sa_http = httplib2.Http(proxy_info=None, timeout=60)
    sa_authorized_http = AuthorizedHttp(sa_creds, http=sa_http)
    sa_run = build('run', 'v2', http=sa_authorized_http)
    
    print("  Attempting to run job...")
    operation = sa_run.projects().locations().jobs().run(
        name=job_name,
        body={}
    ).execute()
    print(f"  OK: Job triggered successfully")
    print(f"  Operation: {operation.get('name')}")
    
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Check recent executions
try:
    print("\n[4/5] Recent Cloud Run Job executions:")
    job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'
    executions = run.projects().locations().jobs().executions().list(
        parent=job_name,
        pageSize=5
    ).execute()
    
    execs = executions.get('executions', [])
    if execs:
        for i, exec_item in enumerate(execs[:3], 1):
            state = exec_item.get('state', 'N/A')
            create_time = exec_item.get('createTime', 'N/A')
            print(f"  Execution {i}: {state} at {create_time}")
    else:
        print("  No executions found")
        
except Exception as e:
    print(f"  ERROR: {e}")

# Try to simulate what scheduler does
try:
    print("\n[5/5] Simulating scheduler call...")
    print("  This is what Cloud Scheduler tries to do:")
    
    job_uri = f"https://{REGION}-run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}:run"
    print(f"  POST {job_uri}")
    print(f"  With OIDC token from: scheduler-invoker@boxwood-chassis-332307.iam.gserviceaccount.com")
    
    # Try making the actual HTTP call
    import requests
    from google.auth.transport.requests import Request
    from google.oauth2 import id_token
    
    # Get OIDC token
    sa_email = "scheduler-invoker@boxwood-chassis-332307.iam.gserviceaccount.com"
    
    # Use service account to get token
    sa_creds = service_account.Credentials.from_service_account_file(
        'service-account-key.json',
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    
    # Request token
    request_obj = Request()
    sa_creds.refresh(request_obj)
    token = sa_creds.token
    
    print(f"  Got access token: {token[:20]}...")
    
    # Try the API call
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(job_uri, headers=headers, json={}, timeout=30)
    print(f"  Response status: {response.status_code}")
    print(f"  Response: {response.text[:500]}")
    
    if response.status_code == 200 or response.status_code == 201:
        print("  SUCCESS: API call works!")
    else:
        print(f"  FAILED: {response.status_code} - {response.text}")
        
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("\nCheck the output above for clues about what's failing.")
print("="*80)
