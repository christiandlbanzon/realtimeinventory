#!/usr/bin/env python3
"""Check scheduler configuration - might be URL or authentication issue"""

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
print("CHECKING SCHEDULER CONFIGURATION")
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

print(f"\n[1/2] Checking scheduler configuration...")
try:
    sched = scheduler.projects().locations().jobs().get(name=scheduler_name).execute()
    
    http_target = sched.get('httpTarget', {})
    uri = http_target.get('uri', '')
    method = http_target.get('httpMethod', '')
    oidc_token = http_target.get('oidcToken', {})
    sa_email = oidc_token.get('serviceAccountEmail', '')
    
    print(f"  URI: {uri}")
    print(f"  Method: {method}")
    print(f"  Service Account: {sa_email}")
    
    # Check if URI format is correct for Cloud Run Jobs API v2
    # The correct format for Cloud Run Jobs v2 API is different
    # It should be: https://{region}-run.googleapis.com/v2/projects/{project}/locations/{region}/jobs/{job}:run
    
    expected_v2_uri = f"https://{REGION}-run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}:run"
    
    print(f"\n  Checking URI format...")
    if '/v1/namespaces/' in uri:
        print(f"  WARNING: URI uses v1 API with 'namespaces'")
        print(f"  Cloud Run Jobs v2 API uses different format")
        print(f"\n  Current (v1): {uri}")
        print(f"  Should be (v2): {expected_v2_uri}")
        print(f"\n  This might be the issue!")
    elif '/v2/' in uri:
        print(f"  OK: URI uses v2 API format")
        if uri == expected_v2_uri:
            print(f"  OK: URI matches expected format")
        else:
            print(f"  WARNING: URI doesn't match expected format")
            print(f"    Expected: {expected_v2_uri}")
            print(f"    Actual: {uri}")
    else:
        print(f"  WARNING: Unknown URI format")
        
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Try to update scheduler with correct v2 API URI
print(f"\n[2/2] Fixing scheduler URI to use v2 API...")
correct_uri = f"https://{REGION}-run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}:run"

scheduler_body = {
    'schedule': '*/5 * * * *',
    'timeZone': 'America/Puerto_Rico',
    'httpTarget': {
        'uri': correct_uri,
        'httpMethod': 'POST',
        'oidcToken': {
            'serviceAccountEmail': '703996360436-compute@developer.gserviceaccount.com'
        }
    }
}

try:
    updated = scheduler.projects().locations().jobs().patch(
        name=scheduler_name,
        body=scheduler_body
    ).execute()
    
    print(f"  OK: Scheduler updated with correct v2 API URI")
    print(f"  New URI: {correct_uri}")
    print(f"\n  The scheduler should now work correctly!")
    print(f"  Wait a few minutes and check if it runs successfully")
    
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()
    print(f"\n  You may need to update it manually:")
    print(f"  1. Go to Cloud Scheduler")
    print(f"  2. Click 'inventory-updater-schedule'")
    print(f"  3. Click 'EDIT'")
    print(f"  4. In 'Configure the execution' section")
    print(f"  5. Update the URL to: {correct_uri}")
    print(f"  6. Click 'UPDATE'")

print("\n" + "="*80)
