#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run VM fix using Python subprocess (bypasses PowerShell issues)
"""

import sys
import subprocess
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

print("="*80)
print("RUNNING VM FIX VIA PYTHON")
print("="*80)
print()

# Change to project directory
project_dir = r"e:\prog fold\Drunken cookies\real-time-inventory"
os.chdir(project_dir)

# Find gcloud
gcloud_paths = [
    r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
    "gcloud",  # Try in PATH
]

gcloud_cmd = None
for path in gcloud_paths:
    if os.path.exists(path) if os.path.sep in path else True:
        try:
            result = subprocess.run([path, "--version"], 
                                  capture_output=True, 
                                  timeout=10,
                                  text=True)
            if result.returncode == 0:
                gcloud_cmd = path
                print(f"✅ Found gcloud: {path}")
                break
        except:
            continue

if not gcloud_cmd:
    print("❌ gcloud not found!")
    print()
    print("Please reinstall gcloud:")
    print("1. Uninstall: Settings → Apps → Google Cloud SDK")
    print("2. Delete: C:\\Users\\banzo\\AppData\\Roaming\\gcloud")
    print("3. Reinstall: https://cloud.google.com/sdk/docs/install")
    sys.exit(1)

print()
print("Step 1: Authenticating...")
try:
    result = subprocess.run(
        [gcloud_cmd, "auth", "activate-service-account", 
         "--key-file=service-account-key.json"],
        cwd=project_dir,
        timeout=30,
        text=True
    )
    if result.returncode == 0:
        print("✅ Authentication successful!")
    else:
        print(f"⚠️  Authentication warning: {result.stderr}")
except Exception as e:
    print(f"⚠️  Authentication issue: {e}")
    print("   Continuing anyway...")

print()
print("Step 2: Setting project...")
try:
    subprocess.run(
        [gcloud_cmd, "config", "set", "project", "boxwood-chassis-332307"],
        cwd=project_dir,
        timeout=10,
        text=True
    )
    print("✅ Project set!")
except Exception as e:
    print(f"⚠️  Warning: {e}")

print()
print("Step 3: Applying fix on VM...")
print()

vm_name = "inventory-updater-vm"
zone = "us-central1-a"
command = "cd /home/banzo && python3 apply_fix_on_vm.py"

try:
    print(f"Executing: gcloud compute ssh {vm_name} --zone={zone} --command=\"{command}\"")
    print()
    
    result = subprocess.run(
        [gcloud_cmd, "compute", "ssh", vm_name, 
         f"--zone={zone}", 
         f"--command={command}"],
        cwd=project_dir,
        timeout=60,
        text=True
    )
    
    print()
    if result.returncode == 0:
        print("="*80)
        print("✅ FIX APPLIED SUCCESSFULLY!")
        print("="*80)
        print()
        print("The promotion quantity fix is now active on the VM.")
        print("Future updates will correctly count items like 'Cheesecake with Biscoff'.")
    else:
        print("="*80)
        print("❌ SSH command failed")
        print("="*80)
        print()
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        print()
        print("MANUAL OPTION:")
        print(f"1. Open PowerShell and run:")
        print(f"   gcloud compute ssh {vm_name} --zone={zone}")
        print(f"2. Once connected, run:")
        print(f"   cd /home/banzo")
        print(f"   python3 apply_fix_on_vm.py")
        
except subprocess.TimeoutExpired:
    print("❌ Command timed out after 60 seconds")
    print("   The VM might be slow to respond, or there's a connection issue.")
except Exception as e:
    print(f"❌ Error: {e}")
    print()
    print("MANUAL OPTION:")
    print(f"1. Open PowerShell and run:")
    print(f"   gcloud compute ssh {vm_name} --zone={zone}")
    print(f"2. Once connected, run:")
    print(f"   cd /home/banzo")
    print(f"   python3 apply_fix_on_vm.py")

print()
