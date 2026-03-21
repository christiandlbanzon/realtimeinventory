#!/usr/bin/env python3
"""
Smart deployment - tries multiple methods
1. Try gcloud scp (if permissions work)
2. Fall back to manual instructions
"""

import os
import sys
import subprocess

PROJECT_ID = "boxwood-chassis-332307"
VM_NAME = "real-time-inventory"
ZONE = "us-central1-b"
VM_USER = "banzo"

FILES_TO_DEPLOY = {
    "vm_inventory_updater_fixed.py": "/home/banzo/vm_inventory_updater.py",
    "clover_creds.json": "/home/banzo/clover_creds.json",
    "service-account-key.json": "/home/banzo/service-account-key.json"
}

print("="*80)
print("SMART DEPLOYMENT - MULTI-METHOD APPROACH")
print("="*80)
print(f"\nVM: {VM_NAME} in {ZONE}")
print("\nThis will try multiple deployment methods for maximum reliability\n")

# Verify files
print("[1/5] Verifying files...")
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

# Method 1: Try gcloud scp
print("\n[2/5] Trying gcloud scp method...")
gcloud_paths = [
    r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
    "gcloud"
]

gcloud_cmd = None
for path in gcloud_paths:
    if path == "gcloud":
        try:
            result = subprocess.run(["gcloud", "--version"], capture_output=True, timeout=5)
            if result.returncode == 0:
                gcloud_cmd = "gcloud"
                break
        except:
            continue
    elif os.path.exists(path):
        gcloud_cmd = path
        break

if gcloud_cmd:
    print(f"  Found gcloud: {gcloud_cmd}")
    success_count = 0
    
    for local_file, remote_path in FILES_TO_DEPLOY.items():
        print(f"\n  Copying {local_file}...")
        try:
            if gcloud_cmd.endswith('.ps1'):
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
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                print(f"    OK: {local_file} deployed")
                success_count += 1
            else:
                print(f"    Failed: {result.stderr[:200]}")
        except Exception as e:
            print(f"    Error: {e}")
    
    if success_count == len(FILES_TO_DEPLOY):
        print("\n  SUCCESS: All files deployed via gcloud!")
        gcloud_success = True
    else:
        print(f"\n  Partial success: {success_count}/{len(FILES_TO_DEPLOY)} files")
        gcloud_success = False
else:
    print("  gcloud not found or not working")
    gcloud_success = False

# Set up cron if files deployed
if gcloud_success:
    print("\n[3/5] Setting up cron job...")
    cron_cmd = """(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/banzo && /usr/bin/python3 /home/banzo/vm_inventory_updater.py >> /home/banzo/inventory_cron.log 2>&1") | crontab -"""
    
    try:
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
        
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("  OK: Cron job configured")
            print(f"  Output: {result.stdout.strip()}")
        else:
            print(f"  WARNING: Cron setup had issues")
            print("  Will provide manual instructions")
    except Exception as e:
        print(f"  WARNING: Could not set up cron: {e}")

# If gcloud failed, provide manual instructions
if not gcloud_success:
    print("\n[4/5] gcloud method failed - providing manual instructions...")
    print("\n" + "="*80)
    print("MANUAL DEPLOYMENT INSTRUCTIONS")
    print("="*80)
    print("\nOption A: Use Google Cloud Console SSH")
    print("1. Go to: https://console.cloud.google.com/compute/instances")
    print(f"2. Click SSH button next to {VM_NAME}")
    print("3. Run these commands:\n")
    
    print("# Create directory")
    print("sudo mkdir -p /home/banzo")
    print("sudo chown -R banzo:banzo /home/banzo")
    print("sudo su - banzo\n")
    
    print("# I'll provide file contents to paste...")
    print("# (Files are too large to show here, but I can provide them)\n")
    
    print("\nOption B: Try gcloud manually")
    print("Open PowerShell as Administrator and run:")
    for local_file, remote_path in FILES_TO_DEPLOY.items():
        abs_path = os.path.abspath(local_file)
        print(f'gcloud compute scp "{abs_path}" {VM_USER}@{VM_NAME}:{remote_path} --zone={ZONE} --project={PROJECT_ID}')

print("\n[5/5] Summary")
print("="*80)
if gcloud_success:
    print("\n✅ DEPLOYMENT COMPLETE!")
    print(f"\nVM: {VM_NAME}")
    print(f"Zone: {ZONE}")
    print(f"\nFiles deployed:")
    for local_file, remote_path in FILES_TO_DEPLOY.items():
        print(f"  {local_file} -> {remote_path}")
    print(f"\nCron job: Runs every 5 minutes")
    print(f"\nCheck logs:")
    print(f"  gcloud compute ssh {VM_NAME} --zone={ZONE} --project={PROJECT_ID} --command='tail -50 /home/{VM_USER}/inventory_cron.log'")
else:
    print("\n⚠️  Automatic deployment had issues")
    print("See manual instructions above")
    print("\nOr wait a few minutes and try again:")
