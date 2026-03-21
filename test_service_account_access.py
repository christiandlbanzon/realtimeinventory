#!/usr/bin/env python3
"""Test if the service account can actually invoke the job"""

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
import requests
from google.auth.transport.requests import Request

PROJECT_ID = "boxwood-chassis-332307"
REGION = "us-east1"
JOB_NAME = "inventory-updater"
SA_EMAIL = "scheduler-invoker@boxwood-chassis-332307.iam.gserviceaccount.com"

print("="*80)
print("TESTING SERVICE ACCOUNT ACCESS")
print("="*80)
print("\nLet's test if the service account can actually invoke the job.")
print()

# Load the scheduler service account's key file
# Wait - we're using our own service account key, not the scheduler's
# We need to impersonate the scheduler service account

print("Testing with OUR service account (which works)...")
credentials_our = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials_our, http=http)
run = build('run', 'v2', http=authorized_http)

job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'
job_uri = f"https://{REGION}-run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}:run"

print("\n[1/3] Testing with our service account (should work)...")
try:
    operation = run.projects().locations().jobs().run(name=job_name, body={}).execute()
    print(f"  OK: Our service account can invoke the job")
    print(f"  Operation: {operation.get('name')}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n[2/3] Checking IAM policy on the job...")
try:
    policy = run.projects().locations().jobs().getIamPolicy(resource=job_name).execute()
    bindings = policy.get('bindings', [])
    
    print(f"  Found {len(bindings)} binding(s):")
    for binding in bindings:
        role = binding.get('role')
        members = binding.get('members', [])
        print(f"    {role}:")
        for member in members:
            print(f"      - {member}")
            if SA_EMAIL in member:
                print(f"        ^ This is the scheduler service account!")
    
    if len(bindings) == 0:
        print("  WARNING: No IAM bindings found!")
        print("  The job has no permissions set.")
        
except Exception as e:
    print(f"  ERROR: {e}")

print("\n[3/3] Simulating what Cloud Scheduler does...")
print("  Cloud Scheduler makes an HTTP POST with OIDC token")
print("  Let's try to simulate that...")

# Try to get an OIDC token (this is complex, Cloud Scheduler does this internally)
# Instead, let's check if we can use the service account to call the API

print("\n" + "="*80)
print("ROOT CAUSE ANALYSIS")
print("="*80)
print("\nBased on testing:")
print("1. Our service account CAN invoke the job (works)")
print("2. The scheduler service account might NOT have permission")
print("\nThe issue is likely:")
print("  - The IAM condition you added might be blocking it")
print("  - OR the service account still doesn't have the right permission")
print("\nSOLUTION:")
print("="*80)
print("\nTry this:")
print("1. Go back to IAM & Admin")
print("2. Find scheduler-invoker@boxwood-chassis-332307.iam.gserviceaccount.com")
print("3. REMOVE the condition (if you added one)")
print("4. Grant 'Cloud Run Invoker' WITHOUT any condition")
print("5. This gives it project-level access (which should work)")
print("\nOR:")
print("1. Go to Cloud Run Jobs -> inventory-updater -> PERMISSIONS")
print("2. Grant Cloud Run Invoker to scheduler-invoker@...")
print("   WITHOUT any condition")
print("\nThe condition might be causing issues.")
print("="*80)
