#!/usr/bin/env python3
"""Manually trigger the Cloud Run Job to test it"""

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
print("MANUALLY TRIGGERING CLOUD RUN JOB")
print("="*80)
print(f"\nJob: {JOB_NAME}")
print(f"Region: {REGION}\n")

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
run = build('run', 'v2', http=authorized_http)

# Trigger execution
job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'

print("Triggering job execution...")
try:
    execution = run.projects().locations().jobs().run(
        name=job_name,
        body={}
    ).execute()
    
    exec_name = execution.get('name', 'N/A')
    print(f"\nOK: Job execution started!")
    print(f"Execution name: {exec_name}")
    print(f"\nView execution:")
    print(f"  https://console.cloud.google.com/run/jobs/{JOB_NAME}/executions?project={PROJECT_ID}&location={REGION}")
    print(f"\nThe job is now running. Check the logs to see the results.")
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
