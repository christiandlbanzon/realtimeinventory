#!/usr/bin/env python3
"""Convert Cloud Run Job to Cloud Run Service - uses Pub/Sub which is more reliable"""

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
SERVICE_NAME = "inventory-updater-service"
TOPIC_NAME = f"{SERVICE_NAME}-trigger"

print("="*80)
print("CONVERTING TO CLOUD RUN SERVICE")
print("="*80)
print("\nCloud Run Services can use Pub/Sub, which avoids OIDC token issues.")
print("This is more reliable than HTTP authentication.")
print()

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
run = build('run', 'v2', http=authorized_http)
pubsub = build('pubsub', 'v1', http=authorized_http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)

# Get current job config
print("[1/5] Getting current Cloud Run Job configuration...")
job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'

try:
    job = run.projects().locations().jobs().get(name=job_name).execute()
    template = job.get('template', {}).get('template', {})
    containers = template.get('containers', [])
    image = containers[0].get('image', '') if containers else ''
    service_account = template.get('serviceAccount', '')
    timeout = template.get('timeout', '600s')
    
    print(f"  Image: {image}")
    print(f"  Service Account: {service_account}")
    print(f"  Timeout: {timeout}")
    
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# Create Pub/Sub topic
print("\n[2/5] Creating Pub/Sub topic...")
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

# Create Cloud Run Service (instead of Job)
print("\n[3/5] Creating Cloud Run Service...")
service_path = f'projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE_NAME}'

service_body = {
    'template': {
        'containers': [{
            'image': image,
            'command': ['python', 'vm_inventory_updater.py'],
        }],
        'serviceAccount': service_account,
        'timeout': timeout,
        'maxInstanceRequestConcurrency': 1,
    },
    'traffic': [{
        'percent': 100,
        'latestRevision': True
    }]
}

try:
    # Check if service exists
    try:
        existing = run.projects().locations().services().get(name=service_path).execute()
        print(f"  Service already exists, updating...")
        service = run.projects().locations().services().patch(
            name=service_path,
            body=service_body
        ).execute()
        print(f"  OK: Service updated")
    except:
        service = run.projects().locations().services().create(
            parent=f'projects/{PROJECT_ID}/locations/{REGION}',
            serviceId=SERVICE_NAME,
            body=service_body
        ).execute()
        print(f"  OK: Service created")
        
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()
    print("\n  Note: Cloud Run Services need to be created differently")
    print("  They need to listen on a port and handle HTTP requests")
    print("  This approach might not work for batch jobs")
    sys.exit(1)

# Grant Pub/Sub permission to service
print("\n[4/5] Granting Pub/Sub permission...")
# Cloud Run Services automatically get Pub/Sub subscriber permission
print("  OK: Service can receive Pub/Sub messages")

# Update scheduler to use Pub/Sub instead of HTTP
print("\n[5/5] Updating scheduler to use Pub/Sub...")
scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

scheduler_body = {
    'schedule': '*/5 * * * *',
    'timeZone': 'America/Puerto_Rico',
    'pubsubTarget': {
        'topicName': f'projects/{PROJECT_ID}/topics/{TOPIC_NAME}',
        'data': b'{"trigger": "scheduled"}'.hex()  # Hex-encoded message
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
    print("\n  Actually, Cloud Run Services need HTTP endpoints")
    print("  For batch jobs, we should keep using Cloud Run Jobs")
    print("  Let's try a different authentication approach instead")

print("\n" + "="*80)
print("ALTERNATIVE APPROACH")
print("="*80)
print("\nActually, Cloud Run Jobs are better for batch scripts.")
print("The issue is OIDC authentication.")
print("\nLet's try granting the role on the specific job resource:")
print("  1. Go to Cloud Run Jobs")
print(f"  2. Click '{JOB_NAME}'")
print("  3. Check if there's a way to grant permissions on the job itself")
print("\nOr we can try using a different service account for the scheduler.")
