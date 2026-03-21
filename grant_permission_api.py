#!/usr/bin/env python3
"""Try to grant permission via API with better error handling"""

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
print("GRANTING PERMISSION VIA API")
print("="*80)

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

try:
    print("\n[1/2] Getting current IAM policy...")
    policy = run.projects().locations().jobs().getIamPolicy(resource=job_name).execute()
    
    bindings = policy.get('bindings', [])
    print(f"  Current bindings: {len(bindings)}")
    
    # Find or create the invoker binding
    invoker_binding = None
    for binding in bindings:
        if binding.get('role') == ROLE:
            invoker_binding = binding
            break
    
    if invoker_binding:
        members = invoker_binding.get('members', [])
        if member in members:
            print(f"  OK: {SA_EMAIL} already has {ROLE}")
            sys.exit(0)
        else:
            print(f"  Adding {SA_EMAIL} to existing {ROLE} binding")
            members.append(member)
    else:
        print(f"  Creating new {ROLE} binding")
        invoker_binding = {
            'role': ROLE,
            'members': [member]
        }
        bindings.append(invoker_binding)
    
    print("\n[2/2] Setting IAM policy...")
    updated_policy = {
        'bindings': bindings,
        'etag': policy.get('etag')
    }
    
    result = run.projects().locations().jobs().setIamPolicy(
        resource=job_name,
        body={'policy': updated_policy}
    ).execute()
    
    print(f"  SUCCESS: Granted {ROLE} to {SA_EMAIL}")
    print(f"  Updated bindings: {len(result.get('bindings', []))}")
    
    print("\n" + "="*80)
    print("PERMISSION GRANTED!")
    print("="*80)
    print("\nNow:")
    print("1. Wait 2-3 minutes for propagation")
    print("2. Manually trigger scheduler to test")
    print("3. It should work now!")
    print("="*80)
    
except Exception as e:
    error_str = str(e)
    print(f"\nERROR: {e}")
    
    if 'PERMISSION_DENIED' in error_str or '403' in error_str:
        print("\n" + "="*80)
        print("CANNOT GRANT VIA API - NEEDS MANUAL ACTION")
        print("="*80)
        print("\nThe service account doesn't have permission to set IAM policies.")
        print("\nMANUAL STEPS:")
        print("-" * 80)
        print("\n1. Go to IAM & Admin:")
        print(f"   https://console.cloud.google.com/iam-admin/iam?project={PROJECT_ID}")
        print("\n2. Click 'GRANT ACCESS' (top of page)")
        print("\n3. In 'New principals', enter:")
        print(f"   {SA_EMAIL}")
        print("\n4. In 'Select a role', choose:")
        print(f"   Cloud Run Invoker")
        print("\n5. Click 'ADD ANOTHER ROLE' and also add:")
        print(f"   Service Account Token Creator")
        print("\n6. IMPORTANT: Click 'CONDITION (OPTIONAL)' or look for")
        print("   'Grant access to specific resources'")
        print("\n7. Select 'Cloud Run Job' as resource type")
        print(f"   Resource name: {JOB_NAME}")
        print(f"   Region: {REGION}")
        print("\n8. Click 'SAVE'")
        print("\n" + "="*80)
        print("\nALTERNATIVE: Use gcloud CLI")
        print("-" * 80)
        print("If you have gcloud installed, run:")
        print()
        print(f'gcloud run jobs add-iam-policy-binding {JOB_NAME} \\')
        print(f'  --region={REGION} \\')
        print(f'  --member="serviceAccount:{SA_EMAIL}" \\')
        print(f'  --role="roles/run.invoker"')
        print()
        print("="*80)
    else:
        import traceback
        traceback.print_exc()
