#!/usr/bin/env python3
"""Deploy files to existing VM via SSH using gcloud"""

import os
import subprocess
import sys

PROJECT_ID = "boxwood-chassis-332307"
ZONE = "us-east1-b"  # Change if your VM is in different zone
VM_NAME = "real-time-inventory"
VM_USER = "banzo"

FILES_TO_DEPLOY = {
    "vm_inventory_updater_fixed.py": "/home/banzo/vm_inventory_updater.py",
    "clover_creds.json": "/home/banzo/clover_creds.json",
    "service-account-key.json": "/home/banzo/service-account-key.json"
}

CRON_COMMAND = """(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/banzo && /usr/bin/python3 /home/banzo/vm_inventory_updater.py >> /home/banzo/inventory_cron.log 2>&1") | crontab -"""

print("="*80)
print("DEPLOY FILES TO EXISTING VM")
print("="*80)
print(f"\nVM: {VM_NAME}")
print(f"Zone: {ZONE}")
print(f"Project: {PROJECT_ID}\n")

# Check files exist
print("[1/4] Checking files...")
for local_file in FILES_TO_DEPLOY.keys():
    if not os.path.exists(local_file):
        print(f"  ERROR: {local_file} not found!")
        sys.exit(1)
    print(f"  OK: {local_file}")

# Find gcloud
print("\n[2/4] Finding gcloud...")
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
            print(f"  OK: Found at {path}")
            break
    except:
        continue

if not gcloud_cmd:
    print("  ERROR: gcloud not found!")
    print("\nPlease install gcloud CLI or deploy files manually via Console SSH")
    sys.exit(1)

# Deploy files
print("\n[3/4] Deploying files...")
for local_file, remote_path in FILES_TO_DEPLOY.items():
    print(f"  Deploying {local_file}...")
    abs_path = os.path.abspath(local_file)
    
    cmd = [
        gcloud_cmd, "compute", "scp",
        abs_path,
        f"{VM_USER}@{VM_NAME}:{remote_path}",
        f"--zone={ZONE}",
        f"--project={PROJECT_ID}"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"    OK: {local_file} deployed")
        else:
            print(f"    ERROR: {result.stderr}")
            print(f"\nManual command:")
            print(f"  gcloud compute scp {abs_path} {VM_USER}@{VM_NAME}:{remote_path} --zone={ZONE} --project={PROJECT_ID}")
    except Exception as e:
        print(f"    ERROR: {e}")
        print(f"\nTry manually:")
        print(f"  gcloud compute scp {abs_path} {VM_USER}@{VM_NAME}:{remote_path} --zone={ZONE} --project={PROJECT_ID}")

# Set up cron
print("\n[4/4] Setting up cron job...")
cmd = [
    gcloud_cmd, "compute", "ssh", VM_NAME,
    f"--zone={ZONE}",
    f"--project={PROJECT_ID}",
    f"--command={CRON_COMMAND}"
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        print("  OK: Cron job set up")
        
        # Verify cron
        verify_cmd = [
            gcloud_cmd, "compute", "ssh", VM_NAME,
            f"--zone={ZONE}",
            f"--project={PROJECT_ID}",
            "--command=crontab -l"
        ]
        verify_result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=30)
        if verify_result.returncode == 0:
            print("\nCron jobs:")
            print(verify_result.stdout)
    else:
        print(f"  ERROR: {result.stderr}")
        print("\nManual command:")
        print(f"  gcloud compute ssh {VM_NAME} --zone={ZONE} --project={PROJECT_ID}")
        print(f"  Then run: {CRON_COMMAND}")
except Exception as e:
    print(f"  ERROR: {e}")
    print("\nManual setup:")
    print(f"  1. SSH: gcloud compute ssh {VM_NAME} --zone={ZONE} --project={PROJECT_ID}")
    print(f"  2. Run: {CRON_COMMAND}")

print("\n" + "="*80)
print("DEPLOYMENT COMPLETE")
print("="*80)
print("\nCheck logs:")
print(f"  gcloud compute ssh {VM_NAME} --zone={ZONE} --project={PROJECT_ID} --command='tail -50 /home/{VM_USER}/inventory_cron.log'")
