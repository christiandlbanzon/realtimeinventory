#!/usr/bin/env python3
"""Grant permission directly on Cloud Run Job - try different approach"""

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
print("GRANTING PERMISSION ON CLOUD RUN JOB")
print("="*80)
print("\nThe service account needs 'Cloud Run Invoker' on the JOB resource itself.")
print("This must be done manually via Console.")
print()

print("MANUAL STEPS:")
print("="*80)
print(f"\n1. Go to Cloud Run Jobs:")
print(f"   https://console.cloud.google.com/run/jobs?project={PROJECT_ID}")
print(f"\n2. Click on '{JOB_NAME}'")
print(f"\n3. Click the 'PERMISSIONS' tab (at the top)")
print(f"\n4. Click '+ GRANT ACCESS'")
print(f"\n5. Add:")
print(f"   Principal: {SA_EMAIL}")
print(f"   Role: Cloud Run Invoker")
print(f"\n6. Click 'SAVE'")
print("\n" + "="*80)
print("\nCRITICAL: This is different from project-level permissions!")
print("The service account needs permission on the SPECIFIC JOB resource.")
print("="*80)

# Try to check current permissions
try:
    credentials = service_account.Credentials.from_service_account_file(
        'service-account-key.json',
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    http = httplib2.Http(proxy_info=None, timeout=60)
    authorized_http = AuthorizedHttp(credentials, http=http)
    run = build('run', 'v2', http=authorized_http)
    
    job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'
    
    print("\n[CHECKING CURRENT PERMISSIONS]")
    policy = run.projects().locations().jobs().getIamPolicy(resource=job_name).execute()
    bindings = policy.get('bindings', [])
    
    if bindings:
        print(f"\n  Found {len(bindings)} binding(s):")
        for binding in bindings:
            role = binding.get('role')
            members = binding.get('members', [])
            print(f"    {role}:")
            for member in members:
                print(f"      - {member}")
                if SA_EMAIL in member:
                    print(f"        ^ This is our service account - OK!")
    else:
        print(f"\n  NO BINDINGS FOUND - This is the problem!")
        print(f"  The job has no IAM permissions set.")
        print(f"  You MUST grant 'Cloud Run Invoker' to {SA_EMAIL}")
        print(f"  on the job resource itself.")
        
except Exception as e:
    print(f"\nCould not check permissions: {e}")
    print("Please follow the manual steps above.")

print("\n" + "="*80)
