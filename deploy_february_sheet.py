#!/usr/bin/env python3
"""
Deploy updated code with February sheet support to VM
"""

import os
import sys
import subprocess

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

VM_NAME = "inventory-updater-vm"
ZONE = "us-central1-a"
SOURCE_FILE = "vm_inventory_updater_fixed.py"
TARGET_PATH = "/home/banzo/vm_inventory_updater.py"

def deploy_to_vm():
    """Deploy the updated file to VM using gcloud scp"""
    print("="*80)
    print("DEPLOYING FEBRUARY SHEET UPDATE TO VM")
    print("="*80)
    
    if not os.path.exists(SOURCE_FILE):
        print(f"❌ Source file not found: {SOURCE_FILE}")
        return False
    
    print(f"\n[1/2] Uploading {SOURCE_FILE} to VM...")
    print(f"      Target: {VM_NAME}:{TARGET_PATH}")
    print(f"      Zone: {ZONE}")
    
    try:
        # Use gcloud scp to deploy (use full path on Windows)
        gcloud_path = r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
        if not os.path.exists(gcloud_path):
            # Try alternative path or just 'gcloud'
            gcloud_path = "gcloud"
        
        cmd = [
            gcloud_path, "compute", "scp",
            SOURCE_FILE,
            f"banzo@{VM_NAME}:{TARGET_PATH}",
            f"--zone={ZONE}",
            "--quiet"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ File uploaded successfully!")
            print(f"   Output: {result.stdout.strip()}")
        else:
            print(f"❌ Upload failed!")
            print(f"   Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Upload timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    print("\n[2/2] Verifying deployment...")
    try:
        # Verify file exists on VM
        gcloud_path = r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
        if not os.path.exists(gcloud_path):
            gcloud_path = "gcloud"
            
        verify_cmd = [
            gcloud_path, "compute", "ssh",
            VM_NAME,
            f"--zone={ZONE}",
            "--command",
            f"ls -lh {TARGET_PATH} && grep -c '1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4' {TARGET_PATH}",
            "--quiet"
        ]
        
        verify_result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=30)
        
        if verify_result.returncode == 0:
            print("✅ Verification successful!")
            print(f"   {verify_result.stdout.strip()}")
        else:
            print("⚠️  Verification had issues (file may still be deployed)")
            print(f"   {verify_result.stderr}")
            
    except Exception as e:
        print(f"⚠️  Could not verify: {e}")
        print("   But file upload appeared successful")
    
    print("\n" + "="*80)
    print("DEPLOYMENT COMPLETE")
    print("="*80)
    print("\n✅ The code will automatically switch to the February sheet")
    print("   when February 1st arrives (or if current date is February+).")
    print("\n📊 Sheet IDs:")
    print("   • January: 1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE")
    print("   • February+: 1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4")
    print("\n⏰ The cron job will use the new code automatically.")
    
    return True

if __name__ == "__main__":
    try:
        success = deploy_to_vm()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
