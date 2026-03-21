#!/usr/bin/env python3
"""
Deploy files to an EXISTING VM
This works even though VM creation was failing!
"""

import os
import sys
import subprocess

PROJECT_ID = "boxwood-chassis-332307"
VM_NAME = "real-time-inventory"
ZONE = "us-central1-b"  # Updated to match the created VM
VM_USER = "banzo"

FILES_TO_DEPLOY = {
    "vm_inventory_updater_fixed.py": "/home/banzo/vm_inventory_updater.py",
    "clover_creds.json": "/home/banzo/clover_creds.json",
    "service-account-key.json": "/home/banzo/service-account-key.json"
}

print("="*80)
print("DEPLOYING TO EXISTING VM")
print("="*80)
print(f"\nVM Name: {VM_NAME}")
print(f"Zone: {ZONE}")
print(f"Project: {PROJECT_ID}")
print("\nThis will deploy files to your existing VM using gcloud scp\n")

# Find gcloud
print("[1/4] Finding gcloud CLI...")
gcloud_paths = [
    r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
    r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.ps1",
    "gcloud"
]

gcloud_cmd = None
for path in gcloud_paths:
    if path == "gcloud":
        try:
            result = subprocess.run(["gcloud", "--version"], capture_output=True, timeout=5)
            if result.returncode == 0:
                gcloud_cmd = "gcloud"
                print(f"  OK: Found gcloud in PATH")
                break
        except:
            continue
    elif os.path.exists(path):
        gcloud_cmd = path
        print(f"  OK: Found gcloud at {path}")
        break

if not gcloud_cmd:
    print("  ERROR: gcloud CLI not found!")
    print("  Install from: https://cloud.google.com/sdk/docs/install")
    sys.exit(1)

# Verify files exist
print("\n[2/4] Verifying files...")
for local_file in FILES_TO_DEPLOY.keys():
    if not os.path.exists(local_file):
        print(f"  ERROR: {local_file} not found!")
        sys.exit(1)
    print(f"  OK: {local_file}")

# Verify February sheet ID
with open("vm_inventory_updater_fixed.py", 'r', encoding='utf-8') as f:
    content = f.read()
    if "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4" in content:
        print("  OK: February sheet ID verified")
    else:
        print("  WARNING: February sheet ID not found!")

# Deploy files
print("\n[3/4] Deploying files via gcloud scp...")
for local_file, remote_path in FILES_TO_DEPLOY.items():
    print(f"\n  Deploying {local_file}...")
    
    if gcloud_cmd.endswith('.ps1'):
        # Use PowerShell wrapper
        cmd = [
            "powershell", "-NoProfile", "-Command",
            f"& '{gcloud_cmd}' compute scp {local_file} {VM_USER}@{VM_NAME}:{remote_path} --zone={ZONE} --project={PROJECT_ID}"
        ]
    else:
        cmd = [
            gcloud_cmd, "compute", "scp",
            local_file,
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
            if "not found" in result.stderr.lower():
                print(f"    Make sure the VM '{VM_NAME}' exists in zone '{ZONE}'")
            sys.exit(1)
    except Exception as e:
        print(f"    ERROR: {e}")
        sys.exit(1)

# Set up cron
print("\n[4/4] Setting up cron job...")
cron_cmd = f"""(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/{VM_USER} && /usr/bin/python3 /home/{VM_USER}/vm_inventory_updater.py >> /home/{VM_USER}/inventory_cron.log 2>&1") | crontab -"""

if gcloud_cmd.endswith('.ps1'):
    ssh_cmd = [
        "powershell", "-NoProfile", "-Command",
        f"& '{gcloud_cmd}' compute ssh {VM_NAME} --zone={ZONE} --project={PROJECT_ID} --command=\"{cron_cmd}\""
    ]
else:
    ssh_cmd = [
        gcloud_cmd, "compute", "ssh",
        VM_NAME,
        f"--zone={ZONE}",
        f"--project={PROJECT_ID}",
        "--command", cron_cmd
    ]

try:
    result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        print("  OK: Cron job configured")
        print(f"  Output: {result.stdout.strip()}")
    else:
        print(f"  WARNING: Cron setup had issues: {result.stderr}")
        print("  You can set it up manually via SSH")
except Exception as e:
    print(f"  WARNING: Could not set up cron: {e}")
    print("  You can set it up manually via SSH")

print("\n" + "="*80)
print("DEPLOYMENT COMPLETE!")
print("="*80)
print(f"\nVM: {VM_NAME}")
print(f"Zone: {ZONE}")
print(f"\nFiles deployed:")
for local_file, remote_path in FILES_TO_DEPLOY.items():
    print(f"  {local_file} -> {remote_path}")
print(f"\nCron job: Runs every 5 minutes")
print(f"\nCheck logs:")
print(f"  gcloud compute ssh {VM_NAME} --zone={ZONE} --project={PROJECT_ID} --command='tail -50 /home/{VM_USER}/inventory_cron.log'")
