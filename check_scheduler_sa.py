#!/usr/bin/env python3
"""Check which service account the scheduler is using"""

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

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)

scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

print("="*80)
print("SCHEDULER SERVICE ACCOUNT CHECK")
print("="*80)

try:
    sched = scheduler.projects().locations().jobs().get(name=scheduler_name).execute()
    http_target = sched.get('httpTarget', {})
    oidc_token = http_target.get('oidcToken', {})
    
    current_sa = oidc_token.get('serviceAccountEmail', 'NOT SET')
    
    print(f"\nCurrent scheduler service account: {current_sa}")
    print(f"\nThis is the service account that needs the roles:")
    print(f"  - Cloud Run Invoker")
    print(f"  - Service Account Token Creator")
    
    if current_sa == "703996360436-compute@developer.gserviceaccount.com":
        print(f"\n⚠️  Still using Compute Engine default service account")
        print(f"   This might have limitations. Consider using the dedicated one.")
    elif "scheduler-invoker" in current_sa:
        print(f"\n✅ Using dedicated service account: {current_sa}")
        print(f"   Grant roles to THIS account (not the Compute Engine one)")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
