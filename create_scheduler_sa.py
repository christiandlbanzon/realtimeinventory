#!/usr/bin/env python3
"""Create dedicated service account for scheduler - avoids self-impersonation issues"""

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
NEW_SA_NAME = "scheduler-invoker"
NEW_SA_EMAIL = f"{NEW_SA_NAME}@{PROJECT_ID}.iam.gserviceaccount.com"

print("="*80)
print("CREATING DEDICATED SERVICE ACCOUNT FOR SCHEDULER")
print("="*80)
print("\nThe Compute Engine default service account might have limitations")
print("for generating OIDC tokens. A dedicated service account should work better.")
print()

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
iam = build('iam', 'v1', http=authorized_http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)
run = build('run', 'v2', http=authorized_http)

# Create service account
print("[1/4] Creating service account...")
sa_path = f'projects/{PROJECT_ID}/serviceAccounts/{NEW_SA_EMAIL}'

try:
    sa = iam.projects().serviceAccounts().create(
        name=f'projects/{PROJECT_ID}',
        body={
            'accountId': NEW_SA_NAME,
            'serviceAccount': {
                'displayName': 'Scheduler Invoker Service Account'
            }
        }
    ).execute()
    print(f"  OK: Created service account {NEW_SA_EMAIL}")
except Exception as e:
    if 'already exists' in str(e).lower():
        print(f"  OK: Service account {NEW_SA_EMAIL} already exists")
    else:
        print(f"  ERROR: {e}")
        print("\n  You may need to create it manually:")
        print(f"  1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts?project={PROJECT_ID}")
        print(f"  2. Click 'CREATE SERVICE ACCOUNT'")
        print(f"  3. Name: {NEW_SA_NAME}")
        print(f"  4. Click 'CREATE AND CONTINUE'")
        print(f"  5. Skip role assignment, click 'DONE'")
        sys.exit(1)

# Grant roles to new service account
print("\n[2/4] Granting roles to new service account...")
print("  Required roles:")
print(f"    - Cloud Run Invoker (on the Cloud Run Job)")
print(f"    - Service Account Token Creator")
print("\n  Grant these manually:")
print(f"  1. Go to: https://console.cloud.google.com/iam-admin/iam?project={PROJECT_ID}")
print(f"  2. Click '+ GRANT ACCESS'")
print(f"  3. Principal: {NEW_SA_EMAIL}")
print(f"  4. Roles:")
print(f"     - Cloud Run Invoker")
print(f"     - Service Account Token Creator")
print(f"  5. Click 'SAVE'")

# Update scheduler to use new service account
print("\n[3/4] Updating scheduler to use new service account...")
scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'
job_uri = f"https://{REGION}-run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}:run"

scheduler_body = {
    'schedule': '*/5 * * * *',
    'timeZone': 'America/Puerto_Rico',
    'httpTarget': {
        'uri': job_uri,
        'httpMethod': 'POST',
        'oidcToken': {
            'serviceAccountEmail': NEW_SA_EMAIL,  # Use new service account
            'audience': job_uri
        }
    }
}

try:
    updated = scheduler.projects().locations().jobs().patch(
        name=scheduler_name,
        body=scheduler_body
    ).execute()
    print(f"  OK: Scheduler updated to use {NEW_SA_EMAIL}")
    print(f"\n  IMPORTANT: Grant the roles above before testing!")
    
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n[4/4] Summary:")
print("="*80)
print(f"\nCreated/Using: {NEW_SA_EMAIL}")
print("\nNext steps:")
print("  1. Grant Cloud Run Invoker role to the new service account")
print("  2. Grant Service Account Token Creator role to the new service account")
print("  3. Wait 2-3 minutes")
print("  4. Manually trigger scheduler to test")
print("\nThis should work because:")
print("  - Dedicated service account (not Compute Engine default)")
print("  - Can generate OIDC tokens without self-impersonation issues")
print("  - Has proper roles granted")

print("\n" + "="*80)
