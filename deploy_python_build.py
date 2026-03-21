#!/usr/bin/env python3
"""
Deploy using Python API to trigger Cloud Build
This bypasses gcloud CLI authentication issues
"""

import os
import sys
import json
import tarfile
import tempfile
import time

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'service-account-key.json'

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.http import MediaFileUpload
import httplib2

PROJECT_ID = "boxwood-chassis-332307"
REGION = "us-east1"
JOB_NAME = "inventory-updater"
BUCKET_NAME = f"{PROJECT_ID}_cloudbuild"

print("="*80)
print("DEPLOYING USING PYTHON API (Bypasses gcloud auth)")
print("="*80)
print(f"\nJob: {JOB_NAME}")
print(f"Region: {REGION}")
print(f"Project: {PROJECT_ID}\n")

# Authenticate
print("[1/6] Authenticating...")
try:
    credentials = service_account.Credentials.from_service_account_file(
        'service-account-key.json',
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    http = httplib2.Http(proxy_info=None, timeout=60)
    authorized_http = AuthorizedHttp(credentials, http=http)
    
    storage = build('storage', 'v1', http=authorized_http)
    cloudbuild = build('cloudbuild', 'v1', http=authorized_http)
    run = build('run', 'v2', http=authorized_http)
    
    print(f"  OK: Authenticated as {credentials.service_account_email}")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# Create Cloud Storage bucket if needed
print("\n[2/6] Setting up Cloud Storage...")
try:
    # Try to get bucket
    storage.buckets().get(bucket=BUCKET_NAME).execute()
    print(f"  OK: Bucket {BUCKET_NAME} exists")
except:
    # Create bucket
    try:
        storage.buckets().insert(
            project=PROJECT_ID,
            body={'name': BUCKET_NAME, 'location': REGION}
        ).execute()
        print(f"  OK: Created bucket {BUCKET_NAME}")
    except Exception as e:
        print(f"  WARNING: Could not create bucket: {e}")
        print(f"  Will try to use existing bucket or create via console")

# Create source archive
print("\n[3/6] Creating source archive...")
with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp:
    archive_path = tmp.name

with tarfile.open(archive_path, 'w:gz') as tar:
    tar.add('Dockerfile', arcname='Dockerfile')
    tar.add('vm_inventory_updater_fixed.py', arcname='vm_inventory_updater_fixed.py')
    tar.add('clover_creds.json', arcname='clover_creds.json')
    tar.add('service-account-key.json', arcname='service-account-key.json')

print(f"  OK: Archive created ({os.path.getsize(archive_path):,} bytes)")

# Upload to Cloud Storage
print("\n[4/6] Uploading to Cloud Storage...")
object_name = f'source/{int(time.time())}.tar.gz'

try:
    media = MediaFileUpload(archive_path, mimetype='application/gzip', resumable=True)
    request = storage.objects().insert(
        bucket=BUCKET_NAME,
        name=object_name,
        media_body=media
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Uploaded {int(status.progress() * 100)}%")
    
    print(f"  OK: Uploaded to gs://{BUCKET_NAME}/{object_name}")
except Exception as e:
    print(f"  ERROR: Upload failed: {e}")
    print(f"\n  Alternative: Use Cloud Shell (easier):")
    print(f"    1. Go to: https://shell.cloud.google.com/")
    print(f"    2. Upload files")
    print(f"    3. Run: gcloud builds submit --tag gcr.io/{PROJECT_ID}/{JOB_NAME}")
    sys.exit(1)

# Trigger Cloud Build
print("\n[5/6] Triggering Cloud Build (this takes 3-5 minutes)...")
build_body = {
    'steps': [{
        'name': 'gcr.io/cloud-builders/docker',
        'args': ['build', '-t', f'gcr.io/{PROJECT_ID}/{JOB_NAME}', '.']
    }],
    'images': [f'gcr.io/{PROJECT_ID}/{JOB_NAME}'],
    'source': {
        'storageSource': {
            'bucket': BUCKET_NAME,
            'object': object_name
        }
    }
}

try:
    operation = cloudbuild.projects().builds().create(
        projectId=PROJECT_ID,
        body=build_body
    ).execute()
    
    build_id = operation['metadata']['build']['id']
    print(f"  OK: Build started (ID: {build_id})")
    print(f"  View: https://console.cloud.google.com/cloud-build/builds/{build_id}?project={PROJECT_ID}")
    print(f"\n  Waiting for build to complete...")
    print(f"  (This takes 3-5 minutes - you can check the link above)")
    
    # Wait for build
    import time
    while True:
        time.sleep(10)
        build_status = cloudbuild.projects().builds().get(
            projectId=PROJECT_ID,
            id=build_id
        ).execute()
        
        status = build_status.get('status')
        if status == 'SUCCESS':
            print(f"\n  OK: Build completed successfully!")
            break
        elif status == 'FAILURE' or status == 'CANCELLED':
            print(f"\n  ERROR: Build {status.lower()}")
            print(f"  Check logs: https://console.cloud.google.com/cloud-build/builds/{build_id}?project={PROJECT_ID}")
            sys.exit(1)
        else:
            print(f"  Status: {status}...")
    
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Create Cloud Run Job
print("\n[6/6] Creating Cloud Run Job...")
job_body = {
    'template': {
        'template': {
            'containers': [{
                'image': f'gcr.io/{PROJECT_ID}/{JOB_NAME}',
            }],
            'serviceAccount': '703996360436-compute@developer.gserviceaccount.com',
            'timeout': '600s',
            'maxRetries': 1
        }
    }
}

parent = f'projects/{PROJECT_ID}/locations/{REGION}'

try:
    result = run.projects().locations().jobs().create(
        parent=parent,
        jobId=JOB_NAME,
        body=job_body
    ).execute()
    print("  OK: Cloud Run Job created!")
except Exception as e:
    if 'already exists' in str(e).lower():
        result = run.projects().locations().jobs().patch(
            name=f'{parent}/jobs/{JOB_NAME}',
            body=job_body
        ).execute()
        print("  OK: Cloud Run Job updated!")
    else:
        print(f"  ERROR: {e}")
        sys.exit(1)

# Cleanup (ignore errors - file might be locked)
try:
    os.unlink(archive_path)
except:
    pass

print("\n" + "="*80)
print("DEPLOYMENT COMPLETE!")
print("="*80)
print(f"\n✅ Cloud Run Job: {JOB_NAME}")
print(f"\nView: https://console.cloud.google.com/run/jobs?project={PROJECT_ID}")
print(f"\nNext: Create Cloud Scheduler to run every 5 minutes")
