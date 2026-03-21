#!/usr/bin/env python3
"""
Deploy to Cloud Run using Python API (no gcloud CLI needed)
"""

import os
import sys
import json
import base64
import tempfile

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
print("DEPLOYING TO CLOUD RUN (Python API)")
print("="*80)
print(f"\nJob: {JOB_NAME}")
print(f"Region: {REGION}")
print(f"Project: {PROJECT_ID}\n")

# Check files
print("[1/4] Checking files...")
if not os.path.exists("vm_inventory_updater_fixed.py"):
    print("  ERROR: vm_inventory_updater_fixed.py not found!")
    sys.exit(1)
if not os.path.exists("clover_creds.json"):
    print("  ERROR: clover_creds.json not found!")
    sys.exit(1)
if not os.path.exists(SERVICE_ACCOUNT_FILE):
    print(f"  ERROR: {SERVICE_ACCOUNT_FILE} not found!")
    sys.exit(1)
print("  OK: All files found")

# Authenticate
print("\n[2/4] Authenticating...")
try:
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    http = httplib2.Http(proxy_info=None, timeout=60)
    authorized_http = AuthorizedHttp(credentials, http=http)
    
    # Need Cloud Build API for building images
    cloudbuild = build('cloudbuild', 'v1', http=authorized_http)
    run = build('run', 'v2', http=authorized_http)
    scheduler = build('cloudscheduler', 'v1', http=authorized_http)
    
    print("  OK: Authenticated")
    print(f"  Service Account: {credentials.service_account_email}")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# Create Dockerfile content
print("\n[3/4] Preparing Docker image...")
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

# Set environment variable
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json

# Run the script
CMD ["python", "vm_inventory_updater.py"]
"""

# Create a temporary directory with files for Docker build
print("  Creating build context...")
with tempfile.TemporaryDirectory() as temp_dir:
    # Write Dockerfile
    dockerfile_path = os.path.join(temp_dir, "Dockerfile")
    with open(dockerfile_path, 'w') as f:
        f.write(dockerfile_content)
    
    # Copy required files
    import shutil
    shutil.copy("vm_inventory_updater_fixed.py", os.path.join(temp_dir, "vm_inventory_updater_fixed.py"))
    shutil.copy("clover_creds.json", os.path.join(temp_dir, "clover_creds.json"))
    shutil.copy(SERVICE_ACCOUNT_FILE, os.path.join(temp_dir, "service-account-key.json"))
    
    # Create .dockerignore
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
    with open(os.path.join(temp_dir, ".dockerignore"), 'w') as f:
        f.write(dockerignore_content)
    
    # Create cloudbuild.yaml
    cloudbuild_yaml = f"""steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', 'gcr.io/{PROJECT_ID}/{JOB_NAME}', '.']
images:
- 'gcr.io/{PROJECT_ID}/{JOB_NAME}'
"""
    with open(os.path.join(temp_dir, "cloudbuild.yaml"), 'w') as f:
        f.write(cloudbuild_yaml)
    
    # Create source archive
    print("  Creating source archive...")
    import tarfile
    archive_path = os.path.join(temp_dir, "source.tar.gz")
    with tarfile.open(archive_path, 'w:gz') as tar:
        tar.add(temp_dir, arcname='.', filter=lambda x: None if os.path.basename(x.name) in ['source.tar.gz'] else x)
    
    # Read archive as base64
    with open(archive_path, 'rb') as f:
        archive_data = f.read()
    
    print("  OK: Build context prepared")

# Build using Cloud Build API
print("\n[4/4] Building Docker image (this may take 3-5 minutes)...")
try:
    build_config = {
        'steps': [{
            'name': 'gcr.io/cloud-builders/docker',
            'args': ['build', '-t', f'gcr.io/{PROJECT_ID}/{JOB_NAME}', '.']
        }],
        'images': [f'gcr.io/{PROJECT_ID}/{JOB_NAME}']
    }
    
    # Upload source
    print("  Uploading source code...")
    # Note: Cloud Build API requires source to be in Cloud Storage or GitHub
    # For simplicity, we'll use inline source
    
    # Actually, Cloud Build API is complex. Let's use a simpler approach:
    # Create the job with a pre-built image or use gcloud commands
    
    print("\n" + "="*80)
    print("CLOUD BUILD API LIMITATION")
    print("="*80)
    print("\nCloud Build API requires source code in Cloud Storage or GitHub.")
    print("For easier deployment, please use one of these options:\n")
    
    print("OPTION 1: Use Google Cloud Console (Easiest)")
    print("-" * 80)
    print("1. Go to: https://console.cloud.google.com/cloud-build/builds?project=" + PROJECT_ID)
    print("2. Click 'Create Build'")
    print("3. Connect to GitHub/Cloud Source Repositories OR")
    print("4. Upload the files manually")
    print("\nOR\n")
    
    print("OPTION 2: Install gcloud CLI (Recommended)")
    print("-" * 80)
    print("Download from: https://cloud.google.com/sdk/docs/install")
    print("Then run:")
    print(f"  gcloud builds submit --tag gcr.io/{PROJECT_ID}/{JOB_NAME}")
    print(f"  gcloud run jobs create {JOB_NAME} \\")
    print(f"    --image gcr.io/{PROJECT_ID}/{JOB_NAME} \\")
    print(f"    --region {REGION} \\")
    print(f"    --service-account {credentials.service_account_email} \\")
    print(f"    --max-retries 1 \\")
    print(f"    --task-timeout 10m")
    print("\nOR\n")
    
    print("OPTION 3: Use Cloud Shell (No installation needed)")
    print("-" * 80)
    print("1. Go to: https://shell.cloud.google.com/")
    print("2. Upload files:")
    print("   - vm_inventory_updater_fixed.py")
    print("   - clover_creds.json")
    print("   - service-account-key.json")
    print("   - Dockerfile (I'll create it)")
    print("3. Run the gcloud commands above")
    
    # Save Dockerfile locally for user
    with open("Dockerfile", 'w') as f:
        f.write(dockerfile_content)
    print(f"\n✅ Dockerfile created: Dockerfile")
    print("   You can use this in Cloud Shell or with gcloud CLI")
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
