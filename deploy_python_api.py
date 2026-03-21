#!/usr/bin/env python3
"""
Deploy to Cloud Run using Python API only (no gcloud auth needed)
Uses service account key file directly
"""

import os
import sys
import json
import base64
import time

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

PROJECT_ID = "boxwood-chassis-332307"
REGION = "us-east1"
JOB_NAME = "inventory-updater"
SERVICE_ACCOUNT_FILE = "service-account-key.json"

print("="*80)
print("DEPLOYING TO CLOUD RUN (Python API - No gcloud auth needed)")
print("="*80)
print(f"\nJob: {JOB_NAME}")
print(f"Region: {REGION}")
print(f"Project: {PROJECT_ID}\n")

# Check files
print("[1/5] Checking files...")
required_files = ["vm_inventory_updater_fixed.py", "clover_creds.json", SERVICE_ACCOUNT_FILE, "Dockerfile"]
for f in required_files:
    if not os.path.exists(f):
        print(f"  ERROR: {f} not found!")
        sys.exit(1)
    print(f"  OK: {f}")

# Authenticate
print("\n[2/5] Authenticating...")
try:
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    http = httplib2.Http(proxy_info=None, timeout=60)
    authorized_http = AuthorizedHttp(credentials, http=http)
    
    cloudbuild = build('cloudbuild', 'v1', http=authorized_http)
    run = build('run', 'v2', http=authorized_http)
    scheduler = build('cloudscheduler', 'v1', http=authorized_http)
    
    print(f"  OK: Authenticated as {credentials.service_account_email}")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# Enable APIs
print("\n[3/5] Enabling APIs...")
serviceusage = build('serviceusage', 'v1', http=authorized_http)
apis_to_enable = [
    'cloudbuild.googleapis.com',
    'run.googleapis.com',
    'cloudscheduler.googleapis.com'
]

for api in apis_to_enable:
    try:
        serviceusage.services().enable(
            name=f'projects/{PROJECT_ID}/services/{api}'
        ).execute()
        print(f"  OK: {api} enabled")
    except Exception as e:
        if "already enabled" in str(e).lower() or "already exists" in str(e).lower():
            print(f"  OK: {api} already enabled")
        else:
            print(f"  WARNING: {api} - {e}")

# Read files for Cloud Build
print("\n[4/5] Preparing build...")
print("  Reading files...")

with open("Dockerfile", 'r') as f:
    dockerfile_content = f.read()

with open("vm_inventory_updater_fixed.py", 'rb') as f:
    script_data = f.read()

with open("clover_creds.json", 'rb') as f:
    clover_data = f.read()

with open(SERVICE_ACCOUNT_FILE, 'rb') as f:
    sa_data = f.read()

# Create build config
print("  Creating build config...")
build_config = {
    'steps': [{
        'name': 'gcr.io/cloud-builders/docker',
        'args': ['build', '-t', f'gcr.io/{PROJECT_ID}/{JOB_NAME}', '.']
    }],
    'images': [f'gcr.io/{PROJECT_ID}/{JOB_NAME}'],
    'source': {
        'storageSource': {
            'bucket': f'{PROJECT_ID}_cloudbuild',
            'object': 'source.tar.gz'
        }
    }
}

print("\n" + "="*80)
print("CLOUD BUILD API LIMITATION")
print("="*80)
print("\nCloud Build API requires source code in Cloud Storage.")
print("The easiest way is to use Cloud Shell (no auth needed there):")
print("\n1. Go to: https://shell.cloud.google.com/")
print("2. Upload these 4 files:")
print("   - vm_inventory_updater_fixed.py")
print("   - clover_creds.json")
print("   - service-account-key.json")
print("   - Dockerfile")
print("\n3. Run:")
print(f"   gcloud builds submit --tag gcr.io/{PROJECT_ID}/{JOB_NAME}")
print(f"   gcloud run jobs create {JOB_NAME} \\")
print(f"     --image gcr.io/{PROJECT_ID}/{JOB_NAME} \\")
print(f"     --region {REGION} \\")
print(f"     --service-account {credentials.service_account_email} \\")
print(f"     --max-retries 1 \\")
print(f"     --task-timeout 10m")
print("\nCloud Shell has gcloud pre-authenticated!")
print("="*80)
