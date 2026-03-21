#!/usr/bin/env python3
"""Try fixing OIDC authentication by checking all requirements"""

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
print("FIXING OIDC AUTHENTICATION")
print("="*80)

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)
run = build('run', 'v2', http=authorized_http)

# Check scheduler config
print("\n[1/3] Checking scheduler OIDC configuration...")
scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

try:
    sched = scheduler.projects().locations().jobs().get(name=scheduler_name).execute()
    http_target = sched.get('httpTarget', {})
    oidc_token = http_target.get('oidcToken', {})
    
    print(f"  OIDC Token Config:")
    print(f"    Service Account: {oidc_token.get('serviceAccountEmail', 'N/A')}")
    print(f"    Audience: {oidc_token.get('audience', 'Not set')}")
    
    # Check if audience is set correctly
    # For Cloud Run Jobs, audience should be the job's URI or left empty
    audience = oidc_token.get('audience')
    if not audience:
        print(f"  INFO: Audience not set - this might be the issue")
        print(f"  For Cloud Run Jobs, audience should be the job URI")
        
except Exception as e:
    print(f"  ERROR: {e}")

# Try updating scheduler with audience set
print("\n[2/3] Updating scheduler with correct audience...")
job_uri = f"https://{REGION}-run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}:run"

scheduler_body = {
    'schedule': '*/5 * * * *',
    'timeZone': 'America/Puerto_Rico',
    'httpTarget': {
        'uri': job_uri,
        'httpMethod': 'POST',
        'oidcToken': {
            'serviceAccountEmail': SA_EMAIL,
            'audience': job_uri  # Set audience to the job URI
        }
    }
}

try:
    updated = scheduler.projects().locations().jobs().patch(
        name=scheduler_name,
        body=scheduler_body
    ).execute()
    print(f"  OK: Scheduler updated with audience set")
    print(f"  Audience: {job_uri}")
    print(f"\n  This might fix the authentication issue!")
    
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n[3/3] Required Roles Checklist:")
print("="*80)
print(f"\nService Account: {SA_EMAIL}")
print("\nRequired roles:")
print("  - Cloud Run Invoker (to invoke the job)")
print("  - Service Account Token Creator (to generate OIDC tokens)")
print("  - Service Account User (might be needed)")
print("\nVerify in IAM & Admin:")
print(f"  https://console.cloud.google.com/iam-admin/iam?project={PROJECT_ID}")

print("\n" + "="*80)
print("NEXT STEPS")
print("="*80)
print("\n1. Wait 2-3 minutes for changes to propagate")
print("2. Manually trigger scheduler via Console")
print("3. Check if authentication succeeds")
print("\nIf still failing, we may need to:")
print("  - Create a dedicated service account for the scheduler")
print("  - Or use a different authentication method")
