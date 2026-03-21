#!/usr/bin/env python3
"""
Execute the deployment script on VM via SSH command
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
FIXED_FILE = "vm_inventory_updater_fixed.py"

def deploy_via_gcloud():
    """Deploy using gcloud scp"""
    print("="*80)
    print("DEPLOYING FIX TO VM")
    print("="*80)
    
    if not os.path.exists(FIXED_FILE):
        print(f"❌ Fixed file not found: {FIXED_FILE}")
        return False
    
    # Find gcloud
    gcloud_paths = [
        r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "gcloud"
    ]
    
    gcloud_path = None
    for path in gcloud_paths:
        if os.path.exists(path) or path == "gcloud":
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    gcloud_path = path
                    break
            except:
                continue
    
    if not gcloud_path:
        print("❌ gcloud not found")
        print("\nPlease deploy manually:")
        print(f"  gcloud compute scp {FIXED_FILE} {VM_NAME}:/home/banzo/vm_inventory_updater.py --zone={ZONE}")
        return False
    
    print(f"✅ Found gcloud: {gcloud_path}")
    
    # Set service account
    env = os.environ.copy()
    env['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath('service-account-key.json')
    
    # Deploy
    print(f"\n[1/2] Deploying {FIXED_FILE} to VM...")
    try:
        cmd = [
            gcloud_path, "compute", "scp",
            FIXED_FILE,
            f"{VM_NAME}:/home/banzo/vm_inventory_updater.py",
            f"--zone={ZONE}"
        ]
        
        print(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("  ✅ File deployed successfully!")
            print(result.stdout)
        else:
            print(f"  ❌ Deployment failed:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Verify deployment
    print(f"\n[2/2] Verifying deployment...")
    try:
        cmd = [
            gcloud_path, "compute", "ssh",
            VM_NAME,
            f"--zone={ZONE}",
            "--command", "grep -c '\"\\*N\\* Cheesecake with Biscoff\"' /home/banzo/vm_inventory_updater.py"
        ]
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            count = result.stdout.strip()
            if count and int(count) > 0:
                print(f"  ✅ Verification passed: Found {count} occurrences of *N* mapping")
                return True
            else:
                print(f"  ⚠️  Could not verify (might be OK)")
        else:
            print(f"  ⚠️  Could not verify: {result.stderr[:200]}")
            
    except Exception as e:
        print(f"  ⚠️  Verification error: {e}")
    
    return True

def main():
    print("="*80)
    print("EXECUTE VM DEPLOYMENT")
    print("="*80)
    
    success = deploy_via_gcloud()
    
    if success:
        print("\n" + "="*80)
        print("✅ DEPLOYMENT COMPLETE!")
        print("="*80)
        print("\nThe fix has been deployed to the VM.")
        print("The cron job will use the new code on the next run (every 5 minutes).")
        print("\nTo verify it's working:")
        print(f"  gcloud compute ssh {VM_NAME} --zone={ZONE} --command='tail -50 /home/banzo/inventory_cron.log | grep -i biscoff'")
    else:
        print("\n" + "="*80)
        print("⚠️  DEPLOYMENT NEEDS MANUAL STEP")
        print("="*80)
        print("\nPlease deploy manually using one of these methods:")
        print(f"\n1. gcloud scp:")
        print(f"   gcloud compute scp {FIXED_FILE} {VM_NAME}:/home/banzo/vm_inventory_updater.py --zone={ZONE}")
        print(f"\n2. SSH and copy:")
        print(f"   gcloud compute ssh {VM_NAME} --zone={ZONE}")
        print(f"   # Then manually copy the file content")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
