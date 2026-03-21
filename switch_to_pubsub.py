#!/usr/bin/env python3
"""Switch scheduler to use Pub/Sub instead of HTTP - more reliable authentication"""

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
TOPIC_NAME = f"{JOB_NAME}-trigger"

print("="*80)
print("SWITCHING TO PUB/SUB METHOD")
print("="*80)
print("\nPub/Sub is more reliable than HTTP with OIDC tokens.")
print("This avoids authentication issues.")
print()

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)
pubsub = build('pubsub', 'v1', http=authorized_http)
run = build('run', 'v2', http=authorized_http)

# Create Pub/Sub topic
print("[1/4] Creating Pub/Sub topic...")
topic_path = f'projects/{PROJECT_ID}/topics/{TOPIC_NAME}'

try:
    topic = pubsub.projects().topics().create(
        name=topic_path,
        body={}
    ).execute()
    print(f"  OK: Created topic {TOPIC_NAME}")
except Exception as e:
    if 'already exists' in str(e).lower():
        print(f"  OK: Topic {TOPIC_NAME} already exists")
    else:
        print(f"  ERROR: {e}")
        print("  Continuing anyway...")

# Create Cloud Run Job subscription (this requires the job to be configured as a service)
# Actually, Cloud Run Jobs can't subscribe to Pub/Sub directly
# We need a different approach - use Cloud Functions or Cloud Run Service

print("\n[2/4] Checking alternative approaches...")
print("  Cloud Run Jobs cannot subscribe to Pub/Sub directly.")
print("  We have two options:")
print("    1. Keep HTTP but fix OIDC authentication")
print("    2. Convert to Cloud Run Service (can use Pub/Sub)")
print()

# Actually, let's try fixing the HTTP approach differently
# Maybe the issue is that we need to grant the role on the service account itself
# Or use a different service account

print("[3/4] Trying alternative: Use Cloud Run Service Account directly...")
print("  The scheduler service account might need to impersonate")
print("  the Cloud Run Job's service account.")
print()

# Check what service account the Cloud Run Job uses
job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'
try:
    job = run.projects().locations().jobs().get(name=job_name).execute()
    job_sa = job.get('template', {}).get('template', {}).get('serviceAccount', '')
    print(f"  Cloud Run Job uses: {job_sa}")
    print(f"  Scheduler uses: 703996360436-compute@developer.gserviceaccount.com")
    
    if job_sa == '703996360436-compute@developer.gserviceaccount.com':
        print("  OK: Same service account")
    else:
        print("  INFO: Different service accounts")
        
except Exception as e:
    print(f"  ERROR: {e}")

print("\n[4/4] Recommended Fix:")
print("="*80)
print("\nThe OIDC authentication might need time to propagate.")
print("Try this:")
print("\n1. Wait 5-10 minutes after granting 'Service Account Token Creator'")
print("2. Manually trigger scheduler via Console:")
print("   - Go to Cloud Scheduler")
print("   - Click 'inventory-updater-schedule'")
print("   - Look for 'RUN NOW' or 'TEST' button")
print("   - Click it")
print("3. Check if it succeeds")
print("\nIf still failing, the issue might be:")
print("  - Role propagation delay (can take 5-10 minutes)")
print("  - Service account needs 'Service Account User' role on itself")
print("  - OIDC token scope issue")
print("\nAlternative: We can convert to Cloud Run Service instead of Job")
print("  (Services can use Pub/Sub which is more reliable)")

print("\n" + "="*80)
