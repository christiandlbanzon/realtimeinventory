#!/usr/bin/env python3
"""Fix scheduler permissions - grant Cloud Run Invoker role"""

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
SA_EMAIL = "703996360436-compute@developer.gserviceaccount.com"

print("="*80)
print("FIXING SCHEDULER PERMISSIONS")
print("="*80)
print(f"\nGranting 'Cloud Run Invoker' role to scheduler service account...")
print(f"Service Account: {SA_EMAIL}")
print(f"Job: {JOB_NAME}\n")

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
run = build('run', 'v2', http=authorized_http)

# Get current IAM policy
job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'

print("[1/3] Getting current IAM policy...")
try:
    policy = run.projects().locations().jobs().getIamPolicy(
        resource=job_name
    ).execute()
    print("  OK: Retrieved current policy")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# Add binding for Cloud Run Invoker role
print("\n[2/3] Adding Cloud Run Invoker role...")

# Check if binding already exists
bindings = policy.get('bindings', [])
invoker_binding = None
for binding in bindings:
    if binding.get('role') == 'roles/run.invoker':
        invoker_binding = binding
        break

if invoker_binding:
    # Add member to existing binding
    members = invoker_binding.get('members', [])
    member = f'serviceAccount:{SA_EMAIL}'
    if member not in members:
        members.append(member)
        print(f"  Added {SA_EMAIL} to existing invoker role")
    else:
        print(f"  {SA_EMAIL} already has invoker role")
else:
    # Create new binding
    new_binding = {
        'role': 'roles/run.invoker',
        'members': [f'serviceAccount:{SA_EMAIL}']
    }
    bindings.append(new_binding)
    print(f"  Created new invoker role binding for {SA_EMAIL}")

policy['bindings'] = bindings

# Set updated policy
print("\n[3/3] Applying updated policy...")
try:
    updated_policy = run.projects().locations().jobs().setIamPolicy(
        resource=job_name,
        body={'policy': policy}
    ).execute()
    print("  OK: Permissions updated!")
    print(f"\n  Service account {SA_EMAIL} now has 'Cloud Run Invoker' role")
    print(f"  Scheduler should now be able to trigger the job")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("PERMISSIONS FIXED!")
print("="*80)
print("\nThe scheduler should now be able to trigger the job.")
print("It will run automatically every 5 minutes.")
print("\nTo verify:")
print("  1. Wait 5 minutes")
print("  2. Check Cloud Run Jobs executions")
print("  3. Or manually trigger: python trigger_job.py")
