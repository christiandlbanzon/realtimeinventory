#!/usr/bin/env python3
"""Convert scheduler to use Pub/Sub - more reliable than HTTP/OIDC"""

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
import json
import base64

PROJECT_ID = "boxwood-chassis-332307"
REGION = "us-east1"
JOB_NAME = "inventory-updater"
TOPIC_NAME = f"{JOB_NAME}-trigger"

print("="*80)
print("CONVERTING TO PUB/SUB (MORE RELIABLE)")
print("="*80)
print("\nPub/Sub avoids OIDC token issues and is more reliable for Cloud Run Jobs.")
print()

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
pubsub = build('pubsub', 'v1', http=authorized_http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)
run = build('run', 'v2', http=authorized_http)

# Step 1: Create Pub/Sub topic
print("[1/3] Creating Pub/Sub topic...")
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
        sys.exit(1)

# Step 2: Update Cloud Run Job to subscribe to Pub/Sub
print("\n[2/3] Updating Cloud Run Job to use Pub/Sub trigger...")
job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'

try:
    # Get current job config
    job = run.projects().locations().jobs().get(name=job_name).execute()
    
    # Note: Cloud Run Jobs don't directly subscribe to Pub/Sub
    # We need to use Cloud Scheduler -> Pub/Sub -> Cloud Run Service
    # OR use Cloud Scheduler -> Pub/Sub -> Cloud Functions -> Cloud Run Job
    
    print("  Note: Cloud Run Jobs don't directly subscribe to Pub/Sub")
    print("  We'll use Cloud Scheduler -> Pub/Sub -> Cloud Run Job via API")
    
except Exception as e:
    print(f"  ERROR: {e}")

# Step 3: Update scheduler to publish to Pub/Sub
print("\n[3/3] Updating scheduler to publish to Pub/Sub...")
scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

# Create message data
message_data = json.dumps({"trigger": "scheduled", "job": JOB_NAME})
message_bytes = message_data.encode('utf-8')

scheduler_body = {
    'schedule': '*/5 * * * *',
    'timeZone': 'America/Puerto_Rico',
    'pubsubTarget': {
        'topicName': f'projects/{PROJECT_ID}/topics/{TOPIC_NAME}',
        'data': base64.b64encode(message_bytes).decode('utf-8')
    }
}

try:
    updated = scheduler.projects().locations().jobs().patch(
        name=scheduler_name,
        body=scheduler_body
    ).execute()
    print(f"  OK: Scheduler updated to use Pub/Sub")
    print(f"  Topic: {TOPIC_NAME}")
    
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()
    print("\n  Actually, Cloud Run Jobs can't directly receive Pub/Sub messages.")
    print("  We need a different approach...")

print("\n" + "="*80)
print("WAIT - BETTER APPROACH")
print("="*80)
print("\nCloud Run Jobs can't receive Pub/Sub directly.")
print("Let's create a Cloud Function that triggers the job when Pub/Sub message arrives.")
print("\nShould I create a Cloud Function to bridge Pub/Sub -> Cloud Run Job?")
print("="*80)
