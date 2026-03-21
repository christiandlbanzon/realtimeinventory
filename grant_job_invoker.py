#!/usr/bin/env python3
"""Grant Cloud Run Invoker role on the specific Cloud Run Job"""

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
ROLE = "roles/run.invoker"

print("="*80)
print("GRANTING CLOUD RUN INVOKER ON JOB RESOURCE")
print("="*80)
print("\nThe service account needs Cloud Run Invoker on the JOB itself,")
print("not just at the project level.")
print()

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
run = build('run', 'v2', http=authorized_http)

job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'

try:
    print("[1/2] Getting current IAM policy for Cloud Run Job...")
    
    # Get current policy
    policy = run.projects().locations().jobs().getIamPolicy(
        resource=job_name
    ).execute()
    
    bindings = policy.get('bindings', [])
    print(f"  Found {len(bindings)} existing bindings")
    
    # Check if role already exists
    invoker_binding = None
    for binding in bindings:
        if binding.get('role') == ROLE:
            invoker_binding = binding
            members = binding.get('members', [])
            sa_member = f'serviceAccount:{SA_EMAIL}'
            if sa_member in members:
                print(f"  OK: Service account already has {ROLE}")
                print(f"  Members: {members}")
                sys.exit(0)
            else:
                print(f"  Found {ROLE} binding, but service account not in members")
                print(f"  Current members: {members}")
                break
    
    # Add service account to binding
    print("\n[2/2] Adding service account to IAM policy...")
    
    sa_member = f'serviceAccount:{SA_EMAIL}'
    
    if invoker_binding:
        # Add to existing binding
        if sa_member not in invoker_binding.get('members', []):
            invoker_binding['members'].append(sa_member)
    else:
        # Create new binding
        invoker_binding = {
            'role': ROLE,
            'members': [sa_member]
        }
        bindings.append(invoker_binding)
    
    # Update policy
    updated_policy = {
        'bindings': bindings,
        'etag': policy.get('etag')
    }
    
    result = run.projects().locations().jobs().setIamPolicy(
        resource=job_name,
        body={'policy': updated_policy}
    ).execute()
    
    print(f"  OK: Granted {ROLE} to {SA_EMAIL} on Cloud Run Job")
    print(f"  Updated bindings: {len(result.get('bindings', []))}")
    
except Exception as e:
    error_str = str(e)
    if 'PERMISSION_DENIED' in error_str or '403' in error_str:
        print(f"  ERROR: Permission denied - cannot set IAM policy programmatically")
        print(f"\n  MANUAL STEPS REQUIRED:")
        print(f"  1. Go to Cloud Run Jobs:")
        print(f"     https://console.cloud.google.com/run/jobs?project={PROJECT_ID}")
        print(f"  2. Click on '{JOB_NAME}'")
        print(f"  3. Click 'PERMISSIONS' tab")
        print(f"  4. Click '+ GRANT ACCESS'")
        print(f"  5. Principal: {SA_EMAIL}")
        print(f"  6. Role: Cloud Run Invoker")
        print(f"  7. Click 'SAVE'")
    else:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*80)
print("After granting permission:")
print("  1. Wait 2-3 minutes for propagation")
print("  2. Manually trigger scheduler to test")
print("  3. Check if it succeeds")
print("="*80)
