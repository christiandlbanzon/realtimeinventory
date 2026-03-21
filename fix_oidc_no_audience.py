#!/usr/bin/env python3
"""Remove audience from OIDC token - it might be causing validation issues"""

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

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)

print("="*80)
print("FIXING OIDC TOKEN CONFIGURATION")
print("="*80)
print("\nRemoving audience field - Cloud Run Jobs API might not require it")
print("and it could be causing validation failures.")
print()

scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'
job_uri = f"https://{REGION}-run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}:run"

# Update scheduler WITHOUT audience
scheduler_body = {
    'schedule': '*/5 * * * *',
    'timeZone': 'America/Puerto_Rico',
    'httpTarget': {
        'uri': job_uri,
        'httpMethod': 'POST',
        'oidcToken': {
            'serviceAccountEmail': SA_EMAIL
            # NO audience field - let it default
        }
    }
}

try:
    print(f"Updating scheduler...")
    updated = scheduler.projects().locations().jobs().patch(
        name=scheduler_name,
        body=scheduler_body
    ).execute()
    
    print(f"  OK: Scheduler updated")
    print(f"  Service Account: {SA_EMAIL}")
    print(f"  Audience: REMOVED (will use default)")
    print(f"  URI: {job_uri}")
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("\n1. Wait 2-3 minutes for changes to propagate")
    print("2. Manually trigger scheduler:")
    print(f"   https://console.cloud.google.com/cloudscheduler?project={PROJECT_ID}")
    print("   Click 'RUN NOW' on inventory-updater-schedule")
    print("\n3. Check if it succeeds")
    print("\nIf it still fails, the issue might be:")
    print("  - Service account needs 'run.jobs.run' permission")
    print("  - Or Cloud Scheduler's OIDC token generation has issues")
    print("="*80)
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    
    # Try alternative: Use the default Compute Engine service account
    print("\n" + "="*80)
    print("ALTERNATIVE: Try using Compute Engine default service account")
    print("="*80)
    print("\nThe Compute Engine default SA might work better:")
    print("  703996360436-compute@developer.gserviceaccount.com")
    print("\nShould I try switching to that?")
    print("="*80)
