#!/usr/bin/env python3
"""Grant permission via API using service account"""

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
import json

PROJECT_ID = "boxwood-chassis-332307"
REGION = "us-east1"
JOB_NAME = "inventory-updater"
SA_EMAIL = "scheduler-invoker@boxwood-chassis-332307.iam.gserviceaccount.com"

print("="*80)
print("GRANTING PERMISSION VIA API")
print("="*80)

# Authenticate with service account
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

try:
    print("\n[1/3] Getting current IAM policy...")
    policy = run.projects().locations().jobs().getIamPolicy(resource=job_name).execute()
    
    bindings = policy.get('bindings', [])
    print(f"  Current bindings: {len(bindings)}")
    
    # Check if already exists
    for binding in bindings:
        if binding.get('role') == role:
            members = binding.get('members', [])
            if member in members:
                print(f"  OK: {SA_EMAIL} already has {role}")
                print("  Permission already granted!")
                sys.exit(0)
    
    print("\n[2/3] Adding service account to policy...")
    # Find or create binding
    invoker_binding = None
    for binding in bindings:
        if binding.get('role') == role:
            invoker_binding = binding
            break
    
    if invoker_binding:
        invoker_binding['members'].append(member)
    else:
        invoker_binding = {'role': role, 'members': [member]}
        bindings.append(invoker_binding)
    
    print("\n[3/3] Setting IAM policy...")
    updated_policy = {
        'bindings': bindings,
        'etag': policy.get('etag')
    }
    
    result = run.projects().locations().jobs().setIamPolicy(
        resource=job_name,
        body={'policy': updated_policy}
    ).execute()
    
    print(f"\n  SUCCESS!")
    print(f"  Granted {role} to {SA_EMAIL}")
    print(f"  Total bindings: {len(result.get('bindings', []))}")
    
    # Verify
    print("\n[VERIFY] Checking updated policy...")
    verify_policy = run.projects().locations().jobs().getIamPolicy(resource=job_name).execute()
    verify_bindings = verify_policy.get('bindings', [])
    for binding in verify_bindings:
        if binding.get('role') == role:
            print(f"  Role {role} members:")
            for m in binding.get('members', []):
                print(f"    - {m}")
                if SA_EMAIL in m:
                    print(f"      ^ Found!")
    
    print("\n" + "="*80)
    print("PERMISSION GRANTED SUCCESSFULLY!")
    print("="*80)
    print("\nNext steps:")
    print("1. Wait 2-3 minutes for propagation")
    print("2. Manually trigger scheduler:")
    print("   https://console.cloud.google.com/cloudscheduler?project=boxwood-chassis-332307")
    print("   Click 'RUN NOW' on inventory-updater-schedule")
    print("3. It should work now!")
    print("="*80)
    
except Exception as e:
    error_str = str(e)
    print(f"\nERROR: {e}")
    
    if 'PERMISSION_DENIED' in error_str or '403' in error_str:
        print("\n" + "="*80)
        print("PERMISSION DENIED - Need Owner/Admin")
        print("="*80)
        print("\nThe service account doesn't have permission to set IAM policies.")
        print("You need to run this as an Owner or Admin.")
        print("\nOPTION 1: Use your user account (not service account)")
        print("-" * 80)
        print("1. Authenticate with your user account:")
        print("   gcloud auth login")
        print("\n2. Then run:")
        print(f'   gcloud run jobs add-iam-policy-binding {JOB_NAME} \\')
        print(f'     --region={REGION} \\')
        print(f'     --member="serviceAccount:{SA_EMAIL}" \\')
        print(f'     --role="roles/run.invoker"')
        print()
        print("OPTION 2: Use Console")
        print("-" * 80)
        print("1. Go to: https://console.cloud.google.com/run/jobs?project={PROJECT_ID}")
        print(f"2. Click on '{JOB_NAME}'")
        print("3. Look for PERMISSIONS tab/button")
        print("4. Grant Cloud Run Invoker to {SA_EMAIL}")
        print("="*80)
    else:
        import traceback
        traceback.print_exc()
