#!/usr/bin/env python3
"""
Create VM using gcloud CLI (alternative to Compute API)
gcloud CLI also uses Compute API but has better retry logic
"""

import os
import sys
import subprocess
import base64

PROJECT_ID = "boxwood-chassis-332307"
ZONE = "us-central1-a"
VM_NAME = "real-time-inventory"
VM_USER = "banzo"
SERVICE_ACCOUNT_FILE = "service-account-key.json"

FILES_TO_DEPLOY = {
    "vm_inventory_updater_fixed.py": "/home/banzo/vm_inventory_updater.py",
    "clover_creds.json": "/home/banzo/clover_creds.json",
    "service-account-key.json": "/home/banzo/service-account-key.json"
}

print("="*80)
print("CREATING VM USING GCLOUD CLI")
print("="*80)
print("\nNote: gcloud CLI also uses Compute API, but has built-in retry logic")
print("This is an alternative if the direct API calls fail.\n")

# Read files and build startup script
print("[1/3] Reading files and building startup script...")
files_content = {}
for local_file, remote_path in FILES_TO_DEPLOY.items():
    if not os.path.exists(local_file):
        print(f"ERROR: {local_file} not found!")
        sys.exit(1)
    with open(local_file, 'r', encoding='utf-8') as f:
        files_content[remote_path] = f.read()
    print(f"  OK: {local_file}")

# Verify February sheet ID
if "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4" in files_content["/home/banzo/vm_inventory_updater.py"]:
    print("  OK: February sheet ID verified")

# Build startup script
startup_script = f"""#!/bin/bash
set -e
exec > /var/log/startup.log 2>&1
echo "=== Startup Script Started ==="
date

apt-get update -y
apt-get install -y python3 python3-pip git

if ! id -u {VM_USER} &>/dev/null; then
    useradd -m -s /bin/bash {VM_USER}
fi

mkdir -p /home/{VM_USER}
chown -R {VM_USER}:{VM_USER} /home/{VM_USER}

pip3 install --upgrade pip
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests python-dotenv fuzzywuzzy python-Levenshtein

cd /home/{VM_USER}
"""

for remote_path, content in files_content.items():
    filename = os.path.basename(remote_path)
    content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    startup_script += f"echo '{content_b64}' | base64 -d > {remote_path}\n"
    startup_script += f"chmod 644 {remote_path}\n"

startup_script += f"""
chmod +x /home/{VM_USER}/vm_inventory_updater.py
(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/{VM_USER} && /usr/bin/python3 /home/{VM_USER}/vm_inventory_updater.py >> /home/{VM_USER}/inventory_cron.log 2>&1") | crontab -
echo "=== Deployment Complete ==="
date
"""

# Save startup script to temp file
startup_file = "startup_script_temp.sh"
with open(startup_file, 'w', encoding='utf-8') as f:
    f.write(startup_script)
print(f"  OK: Startup script saved ({len(startup_script):,} bytes)")

# Find gcloud
print("\n[2/3] Finding gcloud CLI...")
gcloud_base = r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin"
gcloud_paths = [
    os.path.join(gcloud_base, "gcloud.cmd"),
    os.path.join(gcloud_base, "gcloud.ps1"),
    os.path.join(gcloud_base, "gcloud.exe"),
    "gcloud"
]

gcloud_cmd = None
gcloud_is_ps1 = False

for path in gcloud_paths:
    if path == "gcloud":
        # Try if gcloud is in PATH
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
        if path.endswith('.ps1'):
            gcloud_is_ps1 = True
        print(f"  OK: Found gcloud at {path}")
        break

if not gcloud_cmd:
    print("  ERROR: gcloud CLI not found!")
    print("  Install from: https://cloud.google.com/sdk/docs/install")
    sys.exit(1)

# Create VM using gcloud
print("\n[3/3] Creating VM with gcloud...")
print("  This may take 2-5 minutes...")

startup_abs = os.path.abspath(startup_file)

# Build command - use PowerShell wrapper for .ps1 files
if gcloud_is_ps1:
    # For PowerShell scripts, wrap in PowerShell command
    startup_abs_escaped = startup_abs.replace('\\', '\\\\')
    cmd_str = f"""& '{gcloud_cmd}' compute instances create {VM_NAME} --zone={ZONE} --project={PROJECT_ID} --machine-type=e2-micro --image-family=debian-12 --image-project=debian-cloud --boot-disk-size=20GB --boot-disk-type=pd-standard --metadata-from-file startup-script={startup_abs_escaped} --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/spreadsheets --tags=inventory-updater"""
    cmd = ["powershell", "-NoProfile", "-Command", cmd_str]
    print(f"  Using PowerShell wrapper for gcloud.ps1")
else:
    cmd = [
        gcloud_cmd, "compute", "instances", "create", VM_NAME,
        f"--zone={ZONE}",
        f"--project={PROJECT_ID}",
        "--machine-type=e2-micro",
        "--image-family=debian-12",
        "--image-project=debian-cloud",
        "--boot-disk-size=20GB",
        "--boot-disk-type=pd-standard",
        "--metadata-from-file", f"startup-script={startup_abs}",
        "--scopes", "https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/spreadsheets",
        "--tags=inventory-updater"
    ]

try:
    print(f"  Executing gcloud command...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    if result.returncode == 0:
        print("\n" + "="*80)
        print("SUCCESS!")
        print("="*80)
        print(f"\nVM '{VM_NAME}' created successfully!")
        print(f"\nThe startup script will automatically:")
        print(f"  - Install dependencies")
        print(f"  - Deploy all files")
        print(f"  - Set up cron (runs every 5 minutes)")
        print(f"\nCheck status:")
        print(f"  python check_vm_creation_status.py")
    else:
        print(f"\nERROR: {result.stderr}")
        print(f"\nOutput: {result.stdout}")
        sys.exit(1)
        
except subprocess.TimeoutExpired:
    print("\nCommand timed out, but VM creation may still be in progress")
    print("Check status with: python check_vm_creation_status.py")
except Exception as e:
    print(f"\nERROR: {e}")
    sys.exit(1)
finally:
    # Clean up temp file
    if os.path.exists(startup_file):
        os.remove(startup_file)
