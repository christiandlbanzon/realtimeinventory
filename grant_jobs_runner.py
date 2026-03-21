#!/usr/bin/env python3
"""Grant Cloud Run Jobs Runner role - might be needed for API calls"""

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
SA_EMAIL = "scheduler-invoker@boxwood-chassis-332307.iam.gserviceaccount.com"

print("="*80)
print("GRANTING CLOUD RUN JOBS RUNNER ROLE")
print("="*80)
print("\nThe service account might need 'Cloud Run Jobs Runner' role")
print("to call the Cloud Run Jobs API (not just invoke the job).")
print()

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
iam = build('iam', 'v1', http=authorized_http)

print("MANUAL STEPS REQUIRED:")
print("="*80)
print(f"\n1. Go to IAM & Admin:")
print(f"   https://console.cloud.google.com/iam-admin/iam?project={PROJECT_ID}")
print(f"\n2. Find: {SA_EMAIL}")
print(f"\n3. Click the pencil icon to edit")
print(f"\n4. Click '+ ADD ANOTHER ROLE'")
print(f"\n5. Add role: 'Cloud Run Jobs Runner'")
print(f"   (If not found, try 'Cloud Run Admin' or 'Cloud Run Developer')")
print(f"\n6. Click 'SAVE'")
print("\n" + "="*80)
print("\nALTERNATIVELY - Check what exact error you're seeing:")
print("1. Go to Cloud Scheduler")
print("2. Click on 'inventory-updater-schedule'")
print("3. Click 'VIEW LOGS' or check the execution history")
print("4. Look for the exact error message")
print("\nThe error message will tell us exactly what permission is missing.")
print("="*80)
