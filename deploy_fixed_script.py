#!/usr/bin/env python3
"""
Deploy fixed vm_inventory_updater.py to VM
"""

import subprocess
import sys
import os

VM_NAME = "inventory-updater-vm"
VM_ZONE = "us-central1-a"
VM_USER = "banzo"
LOCAL_FILE = "vm_inventory_updater.py"
REMOTE_PATH = "/home/banzo/vm_inventory_updater.py"

def deploy():
    print("="*80)
    print("DEPLOYING FIXED SCRIPT TO VM")
    print("="*80)
    
    if not os.path.exists(LOCAL_FILE):
        print(f"ERROR: {LOCAL_FILE} not found")
        return False
    
    print(f"\n[1/3] Checking gcloud availability...")
    try:
        result = subprocess.run(
            ["gcloud", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("  gcloud is available")
        else:
            print("  ERROR: gcloud not working properly")
            return False
    except FileNotFoundError:
        print("  ERROR: gcloud not found in PATH")
        print("  Please install gcloud CLI or run this manually:")
        print(f"  gcloud compute scp {LOCAL_FILE} {VM_USER}@{VM_NAME}:{REMOTE_PATH} --zone={VM_ZONE}")
        return False
    
    print(f"\n[2/3] Copying {LOCAL_FILE} to VM...")
    try:
        cmd = [
            "gcloud", "compute", "scp",
            LOCAL_FILE,
            f"{VM_USER}@{VM_NAME}:{REMOTE_PATH}",
            f"--zone={VM_ZONE}"
        ]
        
        print(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("  ✅ File copied successfully")
        else:
            print(f"  ERROR: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ERROR: {e}")
        return False
    
    print(f"\n[3/3] Verifying deployment...")
    try:
        cmd = [
            "gcloud", "compute", "ssh",
            f"{VM_USER}@{VM_NAME}",
            f"--zone={VM_ZONE}",
            "--command",
            f"ls -lh {REMOTE_PATH} && head -20 {REMOTE_PATH}"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("  ✅ File verified on VM")
            print("\n" + "="*80)
            print("DEPLOYMENT COMPLETE!")
            print("="*80)
            print("\nThe fixed script is now on the VM.")
            print("The cron job will use the new version on the next run (every 5 minutes).")
            print("\nFixes included:")
            print("  - Cookies & Cream matching (handles 'and' vs '&')")
            print("  - Reliable write method (spreadsheet.batchUpdate)")
            print("  - Better error handling")
            return True
        else:
            print(f"  WARNING: Could not verify: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  WARNING: Could not verify: {e}")
        return False

if __name__ == "__main__":
    success = deploy()
    sys.exit(0 if success else 1)
