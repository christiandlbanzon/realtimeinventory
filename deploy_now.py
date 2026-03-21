#!/usr/bin/env python3
"""Deploy to Cloud Run NOW - using gcloud directly"""

import os
import sys
import subprocess

PROJECT_ID = "boxwood-chassis-332307"
REGION = "us-east1"
JOB_NAME = "inventory-updater"
GCLOUD_PATH = r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

print("="*80)
print("DEPLOYING TO CLOUD RUN NOW")
print("="*80)
print(f"\nJob: {JOB_NAME}")
print(f"Region: {REGION}")
print(f"Project: {PROJECT_ID}\n")

# Check files
print("[1/4] Checking files...")
required_files = [
    "vm_inventory_updater_fixed.py",
    "clover_creds.json",
    "service-account-key.json",
    "Dockerfile"
]

for f in required_files:
    if not os.path.exists(f):
        print(f"  ERROR: {f} not found!")
        sys.exit(1)
    print(f"  OK: {f}")

# Verify gcloud
print("\n[2/4] Verifying gcloud...")
try:
    result = subprocess.run([GCLOUD_PATH, "--version"], capture_output=True, timeout=10)
    if result.returncode == 0:
        print(f"  OK: gcloud found at {GCLOUD_PATH}")
    else:
        print("  ERROR: gcloud not working")
        sys.exit(1)
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# Set project
print("\n[3/4] Setting project...")
try:
    result = subprocess.run([GCLOUD_PATH, "config", "set", "project", PROJECT_ID], 
                          capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        print(f"  OK: Project set to {PROJECT_ID}")
    else:
        print(f"  WARNING: {result.stderr}")
except Exception as e:
    print(f"  WARNING: {e}")

# Build Docker image
print("\n[4/4] Building Docker image (this takes 3-5 minutes)...")
print("  This will:")
print("    1. Build Docker image")
print("    2. Push to Container Registry")
print("    3. Create Cloud Run Job")
print("    4. Set up Cloud Scheduler")
print()

cmd = [GCLOUD_PATH, "builds", "submit", "--tag", f"gcr.io/{PROJECT_ID}/{JOB_NAME}"]

print(f"Running: {' '.join(cmd)}")
print("(This may take several minutes - building Docker image...)")

try:
    # Run with real-time output
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                              text=True, bufsize=1)
    
    for line in process.stdout:
        print(line, end='')
    
    process.wait()
    
    if process.returncode != 0:
        print("\nERROR: Build failed!")
        sys.exit(1)
    
    print("\n✅ Docker image built successfully!")
    
except KeyboardInterrupt:
    print("\n\nBuild interrupted by user")
    sys.exit(1)
except Exception as e:
    print(f"\nERROR: {e}")
    sys.exit(1)

# Create Cloud Run Job
print("\n" + "="*80)
print("CREATING CLOUD RUN JOB")
print("="*80)

cmd = [
    GCLOUD_PATH, "run", "jobs", "create", JOB_NAME,
    "--image", f"gcr.io/{PROJECT_ID}/{JOB_NAME}",
    "--region", REGION,
    "--service-account", "703996360436-compute@developer.gserviceaccount.com",
    "--max-retries", "1",
    "--task-timeout", "10m"
]

print(f"\nRunning: {' '.join(cmd)}")

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    
    if result.returncode != 0:
        if "already exists" in result.stderr.lower():
            print("  Job already exists, updating...")
            cmd[3] = "update"  # Change "create" to "update"
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"ERROR: {result.stderr}")
            sys.exit(1)
    
    print("✅ Cloud Run Job created!")
    print(result.stdout)
    
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Create Cloud Scheduler
print("\n" + "="*80)
print("CREATING CLOUD SCHEDULER (runs every 5 minutes)")
print("="*80)

job_uri = f"https://{REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{PROJECT_ID}/jobs/{JOB_NAME}:run"

cmd = [
    GCLOUD_PATH, "scheduler", "jobs", "create", "http", f"{JOB_NAME}-schedule",
    "--location", REGION,
    "--schedule", "*/5 * * * *",
    "--uri", job_uri,
    "--http-method", "POST",
    "--oauth-service-account-email", "703996360436-compute@developer.gserviceaccount.com"
]

print(f"\nRunning: {' '.join(cmd)}")

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    
    if result.returncode != 0:
        if "already exists" in result.stderr.lower():
            print("  Scheduler already exists, updating...")
            cmd[3] = "update"  # Change "create" to "update"
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"WARNING: {result.stderr}")
            print("\nYou can create scheduler manually later")
        else:
            print("✅ Cloud Scheduler created!")
    else:
        print("✅ Cloud Scheduler created!")
    
except Exception as e:
    print(f"WARNING: {e}")
    print("\nYou can create scheduler manually later")

print("\n" + "="*80)
print("DEPLOYMENT COMPLETE!")
print("="*80)
print(f"\n✅ Cloud Run Job: {JOB_NAME}")
print(f"✅ Scheduler: Runs every 5 minutes")
print(f"\nView in Console:")
print(f"  Jobs: https://console.cloud.google.com/run/jobs?project={PROJECT_ID}")
print(f"  Scheduler: https://console.cloud.google.com/cloudscheduler?project={PROJECT_ID}")
print(f"\nTest run:")
print(f"  {GCLOUD_PATH} run jobs execute {JOB_NAME} --region {REGION}")
