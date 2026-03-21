#!/usr/bin/env python3
"""Manually trigger scheduler to test if authentication works now"""

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

print("="*80)
print("MANUALLY TRIGGERING SCHEDULER TO TEST")
print("="*80)

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)

scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

print(f"\nTriggering scheduler manually...")
print("This will test if authentication works now with the new role.")
print()

try:
    # Run the scheduler job manually
    result = scheduler.projects().locations().jobs().run(
        name=scheduler_name,
        body={}
    ).execute()
    
    print("OK: Scheduler triggered manually!")
    print(f"Check Cloud Scheduler console to see if it succeeds")
    print(f"\nView scheduler:")
    print(f"  https://console.cloud.google.com/cloudscheduler?project={PROJECT_ID}")
    print(f"\nWait 30 seconds, then check:")
    print(f"  1. Cloud Scheduler - last attempt status")
    print(f"  2. Cloud Run Jobs - new execution should appear")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    
    if "permission" in str(e).lower():
        print("\nPermission issue - you may need to trigger it manually via Console")
        print("Go to Cloud Scheduler and click 'RUN NOW' button")

print("\n" + "="*80)
