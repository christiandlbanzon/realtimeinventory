#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run VM fix using service account key directly
Bypasses gcloud credentials.db issues by using GOOGLE_APPLICATION_CREDENTIALS
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
print("RUNNING VM FIX USING SERVICE ACCOUNT KEY")
print("="*80)
print()

# Change to project directory
project_dir = r"e:\prog fold\Drunken cookies\real-time-inventory"
os.chdir(project_dir)

# Set service account as default credentials (bypasses credentials.db)
service_account_path = os.path.join(project_dir, "service-account-key.json")
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = service_account_path

print(f"✅ Using service account: {service_account_path}")
print()

# Find gcloud
gcloud_path = r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
if not os.path.exists(gcloud_path):
    gcloud_path = "gcloud"  # Try PATH

print("Step 1: Authenticating with service account...")
try:
    # Use --quiet to avoid interactive prompts
    result = subprocess.run(
        [gcloud_path, "auth", "activate-service-account", 
         f"--key-file={service_account_path}", "--quiet"],
        cwd=project_dir,
        timeout=30,
        text=True,
        capture_output=True
    )
    if result.returncode == 0:
        print("✅ Authentication successful!")
    else:
        print(f"⚠️  Auth output: {result.stdout}")
        if result.stderr:
            print(f"⚠️  Auth errors: {result.stderr}")
except Exception as e:
    print(f"⚠️  Auth warning: {e}")

print()
print("Step 2: Setting project...")
try:
    result = subprocess.run(
        [gcloud_path, "config", "set", "project", "boxwood-chassis-332307", "--quiet"],
        cwd=project_dir,
        timeout=10,
        text=True,
        capture_output=True
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
    print(f"Executing SSH command...")
    print(f"  VM: {vm_name}")
    print(f"  Zone: {zone}")
    print(f"  Command: {command}")
    print()
    
    # Use --quiet and set no-user-output-enabled to reduce credential.db usage
    result = subprocess.run(
        [gcloud_path, "compute", "ssh", vm_name, 
         f"--zone={zone}", 
         f"--command={command}",
         "--quiet"],
        cwd=project_dir,
        timeout=60,
        text=True,
        env=os.environ.copy()  # Pass environment with GOOGLE_APPLICATION_CREDENTIALS
    )
    
    print()
    if result.returncode == 0:
        print("="*80)
        print("✅ FIX APPLIED SUCCESSFULLY!")
        print("="*80)
        print()
        print("The promotion quantity fix is now active on the VM.")
        print("Future updates will correctly count items like 'Cheesecake with Biscoff'.")
        if result.stdout:
            print("\nOutput:")
            print(result.stdout)
    else:
        print("="*80)
        print("❌ SSH command failed")
        print("="*80)
        print()
        if result.stdout:
            print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print()
        print("MANUAL OPTION:")
        print(f"1. Set environment variable:")
        print(f'   $env:GOOGLE_APPLICATION_CREDENTIALS="{service_account_path}"')
        print(f"2. Then run:")
        print(f"   gcloud compute ssh {vm_name} --zone={zone}")
        print(f"3. Once connected, run:")
        print(f"   cd /home/banzo")
        print(f"   python3 apply_fix_on_vm.py")
        
except subprocess.TimeoutExpired:
    print("❌ Command timed out after 60 seconds")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()
