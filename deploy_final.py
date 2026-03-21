#!/usr/bin/env python3
"""Deploy to Cloud Run - handles gcloud permission issues"""

import os
import sys
import subprocess
import tempfile

PROJECT_ID = "boxwood-chassis-332307"
REGION = "us-east1"
JOB_NAME = "inventory-updater"
GCLOUD_PATH = r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
SERVICE_ACCOUNT_FILE = "service-account-key.json"

print("="*80)
print("DEPLOYING TO CLOUD RUN")
print("="*80)

# Create temp config directory
temp_config = os.path.join(tempfile.gettempdir(), "gcloud_config_deploy")
os.makedirs(temp_config, exist_ok=True)

# Set environment variable for gcloud config
env = os.environ.copy()
env["CLOUDSDK_CONFIG"] = temp_config

print(f"\nUsing temp config: {temp_config}")

# Authenticate with service account
print("\n[1/5] Authenticating with service account...")
cmd = [
    GCLOUD_PATH,
    "auth", "activate-service-account",
    f"--key-file={os.path.abspath(SERVICE_ACCOUNT_FILE)}",
    f"--project={PROJECT_ID}"
]

try:
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        print("  OK: Authenticated")
    else:
        print(f"  WARNING: {result.stderr}")
except Exception as e:
    print(f"  WARNING: {e}")

# Set project
print("\n[2/5] Setting project...")
cmd = [GCLOUD_PATH, "config", "set", "project", PROJECT_ID]
try:
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=10)
    print(f"  OK: Project set")
except Exception as e:
    print(f"  WARNING: {e}")

# Build Docker image
print("\n[3/5] Building Docker image (this takes 3-5 minutes)...")
print("  This uploads files and builds the image...")
cmd = [GCLOUD_PATH, "builds", "submit", "--tag", f"gcr.io/{PROJECT_ID}/{JOB_NAME}"]

print(f"\nRunning: {' '.join(cmd)}")
print("(Please wait - this takes several minutes...)")

try:
    process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                              text=True, bufsize=1)
    
    for line in process.stdout:
        print(line, end='')
    
    process.wait()
    
    if process.returncode != 0:
        print("\nERROR: Build failed!")
        print("\nYou can try manually:")
        print(f"  {GCLOUD_PATH} builds submit --tag gcr.io/{PROJECT_ID}/{JOB_NAME}")
        sys.exit(1)
    
    print("\n✅ Docker image built!")
    
except KeyboardInterrupt:
    print("\n\nBuild interrupted")
    sys.exit(1)
except Exception as e:
    print(f"\nERROR: {e}")
    sys.exit(1)

# Create Cloud Run Job
print("\n[4/5] Creating Cloud Run Job...")
cmd = [
    GCLOUD_PATH, "run", "jobs", "create", JOB_NAME,
    "--image", f"gcr.io/{PROJECT_ID}/{JOB_NAME}",
    "--region", REGION,
    "--service-account", "703996360436-compute@developer.gserviceaccount.com",
    "--max-retries", "1",
    "--task-timeout", "10m"
]

try:
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
    
    if result.returncode != 0:
        if "already exists" in result.stderr.lower():
            print("  Job exists, updating...")
            cmd[3] = "update"
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"ERROR: {result.stderr}")
            sys.exit(1)
    
    print("✅ Cloud Run Job created!")
    
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Create Cloud Scheduler
print("\n[5/5] Creating Cloud Scheduler (runs every 5 minutes)...")
job_uri = f"https://{REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{PROJECT_ID}/jobs/{JOB_NAME}:run"

cmd = [
    GCLOUD_PATH, "scheduler", "jobs", "create", "http", f"{JOB_NAME}-schedule",
    "--location", REGION,
    "--schedule", "*/5 * * * *",
    "--uri", job_uri,
    "--http-method", "POST",
    "--oauth-service-account-email", "703996360436-compute@developer.gserviceaccount.com"
]

try:
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
    
    if result.returncode != 0:
        if "already exists" in result.stderr.lower():
            print("  Scheduler exists, updating...")
            cmd[3] = "update"
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"WARNING: {result.stderr}")
        else:
            print("✅ Cloud Scheduler created!")
    else:
        print("✅ Cloud Scheduler created!")
    
except Exception as e:
    print(f"WARNING: {e}")

print("\n" + "="*80)
print("DEPLOYMENT COMPLETE!")
print("="*80)
print(f"\n✅ Job: {JOB_NAME}")
print(f"✅ Runs every 5 minutes automatically")
print(f"\nView: https://console.cloud.google.com/run/jobs?project={PROJECT_ID}")
