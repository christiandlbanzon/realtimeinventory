#!/usr/bin/env python3
"""Grant Cloud Run Invoker permission via IAM & Admin"""

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
print("GRANTING CLOUD RUN INVOKER PERMISSION")
print("="*80)
print(f"\nService Account: {SA_EMAIL}")
print(f"Role: Cloud Run Invoker")
print(f"Resource: Cloud Run Job '{JOB_NAME}'")
print()

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)

# Try using Cloud Resource Manager API
print("[1/2] Attempting to grant permission via API...")
try:
    crm = build('cloudresourcemanager', 'v1', http=authorized_http)
    
    # Get current IAM policy for the project
    policy = crm.projects().getIamPolicy(
        resource=PROJECT_ID,
        body={}
    ).execute()
    
    # Check if binding exists
    bindings = policy.get('bindings', [])
    invoker_binding = None
    for binding in bindings:
        if binding.get('role') == 'roles/run.invoker':
            invoker_binding = binding
            break
    
    member = f'serviceAccount:{SA_EMAIL}'
    
    if invoker_binding:
        members = invoker_binding.get('members', [])
        if member not in members:
            members.append(member)
            print(f"  Adding {SA_EMAIL} to existing Cloud Run Invoker role")
        else:
            print(f"  {SA_EMAIL} already has Cloud Run Invoker role at project level")
    else:
        new_binding = {
            'role': 'roles/run.invoker',
            'members': [member]
        }
        bindings.append(new_binding)
        print(f"  Creating new Cloud Run Invoker role binding")
    
    policy['bindings'] = bindings
    
    # Set updated policy
    updated_policy = crm.projects().setIamPolicy(
        resource=PROJECT_ID,
        body={'policy': policy}
    ).execute()
    
    print("  OK: Permission granted at project level!")
    print("\n  Note: This grants permission for all Cloud Run resources in the project.")
    print("  The scheduler should now be able to trigger the job.")
    
except Exception as e:
    error_str = str(e)
    if "permission" in error_str.lower() or "403" in error_str:
        print(f"  ERROR: Don't have permission to set IAM policies")
        print(f"\n  You need to grant this permission manually via Console.")
    else:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()

print("\n[2/2] Manual Steps (if API failed):")
print("="*80)
print("\nGo to IAM & Admin:")
print(f"  https://console.cloud.google.com/iam-admin/iam?project={PROJECT_ID}")
print("\nSteps:")
print("  1. Click 'GRANT ACCESS' button at the top")
print(f"  2. In 'New principals', enter: {SA_EMAIL}")
print("  3. In 'Select a role', search for: Cloud Run Invoker")
print("  4. Select 'Cloud Run Invoker' role")
print("  5. Click 'SAVE'")
print("\nAfter granting permission:")
print("  1. Go to Cloud Scheduler:")
print(f"     https://console.cloud.google.com/cloudscheduler?project={PROJECT_ID}")
print("  2. Click 'inventory-updater-schedule'")
print("  3. Click 'EDIT' then 'SAVE' (to reschedule)")
print("  4. Check that 'Next run' shows a future time")

print("\n" + "="*80)
