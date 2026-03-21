#!/usr/bin/env python3
"""
Execute deployment on the new VM
"""

import subprocess
import sys
import time

VM_NAME = "inventory-updater-vm-new"
ZONE = "us-central1-a"
PROJECT = "boxwood-chassis-332307"

def execute_via_ssh(command, description):
    """Execute command on VM via gcloud compute ssh"""
    print(f"\n{description}...")
    
    cmd = [
        "gcloud", "compute", "ssh", VM_NAME,
        "--zone", ZONE,
        "--project", PROJECT,
        "--command", command,
        "--quiet"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"✅ {description} completed")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"⚠️  {description} had issues:")
            print(result.stderr[:500])
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("="*80)
    print("EXECUTING DEPLOYMENT ON NEW VM")
    print("="*80)
    
    # Deploy files
    deploy_cmd = "curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-files | bash"
    execute_via_ssh(deploy_cmd, "Deploying files")
    
    # Wait a bit
    time.sleep(2)
    
    # Set up cron
    cron_cmd = "curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/setup-cron | bash"
    execute_via_ssh(cron_cmd, "Setting up cron job")
    
    # Verify deployment
    verify_cmd = "ls -lh /home/banzo/vm_inventory_updater.py /home/banzo/clover_creds.json /home/banzo/service-account-key.json && crontab -l"
    execute_via_ssh(verify_cmd, "Verifying deployment")
    
    print("\n" + "="*80)
    print("✅ DEPLOYMENT COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
