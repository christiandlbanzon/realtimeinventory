#!/usr/bin/env python3
"""Fix HTTP 401 UNAUTHENTICATED error"""

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
print("FIXING HTTP 401 UNAUTHENTICATED ERROR")
print("="*80)
print("\nError: UNAUTHENTICATED (HTTP 401)")
print("The OIDC token is being rejected.")
print("\nThe service account needs permission on the JOB RESOURCE itself.")
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
member = f'serviceAccount:{SA_EMAIL}'
role = 'roles/run.invoker'

print("Attempting to grant permission on job resource...")
try:
    # Get current policy
    policy = run.projects().locations().jobs().getIamPolicy(resource=job_name).execute()
    
    bindings = policy.get('bindings', [])
    
    # Find or create invoker binding
    invoker_binding = None
    for binding in bindings:
        if binding.get('role') == role:
            invoker_binding = binding
            break
    
    if invoker_binding:
        if member not in invoker_binding.get('members', []):
            invoker_binding['members'].append(member)
    else:
        invoker_binding = {'role': role, 'members': [member]}
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
    
    print(f"SUCCESS: Granted {role} to {SA_EMAIL} on job resource")
    print(f"Updated bindings: {len(result.get('bindings', []))}")
    
    print("\n" + "="*80)
    print("PERMISSION GRANTED!")
    print("="*80)
    print("\nWait 2-3 minutes, then manually trigger scheduler.")
    print("It should work now!")
    print("="*80)
    
except Exception as e:
    error_str = str(e)
    if 'PERMISSION_DENIED' in error_str or '403' in error_str:
        print("ERROR: Cannot grant permission via API")
        print("\n" + "="*80)
        print("USE GCLOUD COMMAND INSTEAD")
        print("="*80)
        print("\nRun this command in your terminal:")
        print()
        print(f'gcloud run jobs add-iam-policy-binding {JOB_NAME} \\')
        print(f'  --region={REGION} \\')
        print(f'  --member="serviceAccount:{SA_EMAIL}" \\')
        print(f'  --role="roles/run.invoker"')
        print()
        print("This grants permission directly on the job resource.")
        print("After running this, wait 2-3 minutes and test.")
        print("="*80)
    else:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
