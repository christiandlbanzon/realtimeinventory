#!/usr/bin/env python3
"""Fix authentication issue - service account needs Service Account Token Creator"""

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
SA_EMAIL = "703996360436-compute@developer.gserviceaccount.com"

print("="*80)
print("FIXING AUTHENTICATION ISSUE")
print("="*80)
print(f"\nError: UNAUTHENTICATED (401)")
print(f"Service Account: {SA_EMAIL}")
print()

print("The scheduler uses OIDC token authentication.")
print("The service account needs 'Service Account Token Creator' role")
print("to generate OIDC tokens for authentication.")
print()

print("="*80)
print("MANUAL FIX REQUIRED")
print("="*80)
print("\nGo to IAM & Admin:")
print(f"  https://console.cloud.google.com/iam-admin/iam?project={PROJECT_ID}")
print("\nSteps:")
print("  1. Find: 703996360436-compute@developer.gserviceaccount.com")
print("  2. Click the pencil icon (edit) next to it")
print("  3. Click '+ ADD ANOTHER ROLE'")
print("  4. Search for: Service Account Token Creator")
print("  5. Select 'Service Account Token Creator'")
print("  6. Click 'SAVE'")
print("\nOR use 'Grant Access' button:")
print("  1. Click '+ GRANT ACCESS'")
print(f"  2. Principal: {SA_EMAIL}")
print("  3. Role: Service Account Token Creator")
print("  4. Click 'SAVE'")
print()

print("="*80)
print("WHY THIS IS NEEDED")
print("="*80)
print("\nCloud Scheduler uses OIDC tokens to authenticate with Cloud Run.")
print("To generate OIDC tokens, the service account needs:")
print("  - Cloud Run Invoker (already granted)")
print("  - Service Account Token Creator (MISSING - needs to be granted)")
print("\nWithout 'Service Account Token Creator', the scheduler cannot")
print("generate the OIDC token needed to authenticate with Cloud Run Jobs.")

print("\n" + "="*80)
