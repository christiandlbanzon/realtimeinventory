#!/usr/bin/env python3
"""
Deploy inventory updater as Cloud Run Job (Modern GCP approach)
This is the 2025 recommended way - serverless, pay-per-use, more reliable
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

PROJECT_ID = "boxwood-chassis-332307"
REGION = "us-east1"  # Cloud Run region
JOB_NAME = "inventory-updater"
SERVICE_ACCOUNT_FILE = "service-account-key.json"

print("="*80)
print("DEPLOYING AS CLOUD RUN JOB (Modern Approach)")
print("="*80)
print(f"\nJob Name: {JOB_NAME}")
print(f"Region: {REGION}")
print(f"Project: {PROJECT_ID}\n")

# Check files
print("[1/5] Checking files...")
REQUIRED_FILES = {
    "vm_inventory_updater_fixed.py": "Main script",
    "clover_creds.json": "Clover credentials",
    "service-account-key.json": "Service account"
}

for filename, desc in REQUIRED_FILES.items():
    if not os.path.exists(filename):
        print(f"  ERROR: {filename} not found!")
        sys.exit(1)
    print(f"  OK: {filename}")

# Create Dockerfile
print("\n[2/5] Creating Dockerfile...")
dockerfile_content = """FROM python:3.12-slim

WORKDIR /app

# Copy credentials
COPY clover_creds.json .
COPY service-account-key.json .

# Copy main script
COPY vm_inventory_updater_fixed.py vm_inventory_updater.py

# Install dependencies
RUN pip install --no-cache-dir \\
    google-auth \\
    google-auth-oauthlib \\
    google-auth-httplib2 \\
    google-api-python-client \\
    requests \\
    python-dotenv \\
    fuzzywuzzy \\
    python-Levenshtein

# Set environment variable for service account
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json

# Run the script
CMD ["python", "vm_inventory_updater.py"]
"""

with open("Dockerfile", 'w') as f:
    f.write(dockerfile_content)
print("  OK: Dockerfile created")

# Create .dockerignore
print("\n[3/5] Creating .dockerignore...")
dockerignore_content = """__pycache__
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info
dist
build
.venv
venv
.env
*.log
.git
.gcloud_temp_config
*.md
*.txt
*.ps1
*.bat
*.sh
!vm_inventory_updater_fixed.py
!clover_creds.json
!service-account-key.json
"""

with open(".dockerignore", 'w') as f:
    f.write(dockerignore_content)
print("  OK: .dockerignore created")

# Authenticate
print("\n[4/5] Authenticating...")
try:
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    http = httplib2.Http(proxy_info=None, timeout=30)
    authorized_http = AuthorizedHttp(credentials, http=http)
    cloudbuild = build('cloudbuild', 'v1', http=authorized_http)
    run = build('run', 'v2', http=authorized_http)
    scheduler = build('cloudscheduler', 'v1', http=authorized_http)
    print("  OK: Authenticated")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# Build and deploy using gcloud (more reliable than API)
print("\n[5/5] Building and deploying...")
print("  This will:")
print("    1. Build Docker image")
print("    2. Push to Container Registry")
print("    3. Create/Update Cloud Run Job")
print("    4. Set up Cloud Scheduler (runs daily at 1 AM Puerto Rico = 5 AM UTC)")

# Find gcloud
gcloud_paths = [
    r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
    r"C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
    r"C:\Users\{}\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd".format(os.getenv('USERNAME')),
    "gcloud"
]

gcloud_cmd = None
for path in gcloud_paths:
    try:
        result = subprocess.run([path, "--version"], capture_output=True, timeout=5)
        if result.returncode == 0:
            gcloud_cmd = path
            break
    except:
        continue

if not gcloud_cmd:
    print("\n" + "="*80)
    print("MANUAL DEPLOYMENT REQUIRED")
    print("="*80)
    print("\ngcloud CLI not found. Please run these commands manually:\n")
    print(f"# 1. Build and deploy Cloud Run Job")
    print(f"gcloud builds submit --tag gcr.io/{PROJECT_ID}/{JOB_NAME}")
    print(f"gcloud run jobs create {JOB_NAME} \\")
    print(f"  --image gcr.io/{PROJECT_ID}/{JOB_NAME} \\")
    print(f"  --region {REGION} \\")
    print(f"  --service-account {credentials.service_account_email} \\")
    print(f"  --max-retries 1 \\")
    print(f"  --task-timeout 10m")
    print(f"\n# 2. Create Cloud Scheduler job (runs every 5 minutes)")
    print(f"gcloud scheduler jobs create http {JOB_NAME}-schedule \\")
    print(f"  --location {REGION} \\")
    print(f"  --schedule '*/5 * * * *' \\")
    print(f"  --uri https://{REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{PROJECT_ID}/jobs/{JOB_NAME}:run \\")
    print(f"  --http-method POST \\")
    print(f"  --oauth-service-account-email {credentials.service_account_email}")
    sys.exit(1)

print(f"\nUsing gcloud at: {gcloud_cmd}")

# Step 1: Build Docker image
print("\n  Step 1: Building Docker image...")
cmd = [
    gcloud_cmd, "builds", "submit",
    "--tag", f"gcr.io/{PROJECT_ID}/{JOB_NAME}",
    "--project", PROJECT_ID
]

try:
    result = subprocess.run(cmd, timeout=600)  # 10 min timeout
    if result.returncode != 0:
        print("  ERROR: Docker build failed")
        print("  Try running manually:")
        print(f"    {' '.join(cmd)}")
        sys.exit(1)
    print("  OK: Image built")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# Step 2: Create Cloud Run Job
print("\n  Step 2: Creating Cloud Run Job...")
cmd = [
    gcloud_cmd, "run", "jobs", "create", JOB_NAME,
    "--image", f"gcr.io/{PROJECT_ID}/{JOB_NAME}",
    "--region", REGION,
    "--project", PROJECT_ID,
    "--service-account", credentials.service_account_email,
    "--max-retries", "1",
    "--task-timeout", "10m"
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        if "already exists" in result.stderr.lower():
            print("  Job already exists, updating...")
            cmd[2] = "update"  # Change "create" to "update"
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr}")
            sys.exit(1)
    print("  OK: Cloud Run Job created")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# Step 3: Create Cloud Scheduler (daily at 1 AM Puerto Rico = 5 AM UTC)
print("\n  Step 3: Creating Cloud Scheduler (runs daily at 1 AM Puerto Rico = 5 AM UTC)...")
job_uri = f"https://{REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{PROJECT_ID}/jobs/{JOB_NAME}:run"

cmd = [
    gcloud_cmd, "scheduler", "jobs", "create", "http", f"{JOB_NAME}-schedule",
    "--location", REGION,
    "--project", PROJECT_ID,
    "--schedule", "0 5 * * *",  # Daily at 5 AM UTC = 1 AM Puerto Rico (end-of-day run)
    "--uri", job_uri,
    "--http-method", "POST",
    "--oauth-service-account-email", credentials.service_account_email
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        if "already exists" in result.stderr.lower():
            print("  Scheduler already exists, updating...")
            cmd[3] = "update"  # Change "create" to "update"
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"  WARNING: {result.stderr}")
            print("  You can create scheduler manually:")
            print(f"    {' '.join(cmd)}")
    else:
        print("  OK: Cloud Scheduler created")
except Exception as e:
    print(f"  WARNING: {e}")
    print("  You can create scheduler manually later")

print("\n" + "="*80)
print("DEPLOYMENT COMPLETE!")
print("="*80)
print(f"\n✅ Cloud Run Job: {JOB_NAME}")
print(f"✅ Scheduler: Runs daily at 1 AM Puerto Rico (5 AM UTC)")
print(f"   - Processes yesterday's data (end-of-day finalization)")
print(f"   - Updates both primary sheet and Drunken Cookies sheet")
print(f"   - Includes fixes: FOR_DATE support, Plaza/PlazaSol/VSJ mapping")
print(f"\nView job:")
print(f"  https://console.cloud.google.com/run/jobs?project={PROJECT_ID}")
print(f"\nView scheduler:")
print(f"  https://console.cloud.google.com/cloudscheduler?project={PROJECT_ID}")
print(f"\nTest run manually:")
print(f"  gcloud run jobs execute {JOB_NAME} --region {REGION} --project {PROJECT_ID}")
