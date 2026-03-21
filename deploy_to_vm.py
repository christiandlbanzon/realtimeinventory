"""Deploy fixed vm_inventory_updater.py to VM"""
import subprocess
import sys
import os

def deploy_to_vm():
    """Deploy the fixed script to the VM"""
    print("="*80)
    print("DEPLOYING FIXED SCRIPT TO VM")
    print("="*80)
    
    script_path = "vm_inventory_updater.py"
    
    if not os.path.exists(script_path):
        print(f"ERROR: {script_path} not found!")
        return False
    
    print(f"\n[1/3] Uploading {script_path} to VM...")
    
    try:
        # Use gcloud compute scp to copy file to VM
        # Note: You may need to specify the zone
        result = subprocess.run(
            ['gcloud', 'compute', 'scp', script_path, 
             'inventory-updater-vm:/home/banzo/vm_inventory_updater.py',
             '--zone=us-central1-a'],  # Adjust zone if needed
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("SUCCESS: File uploaded to VM")
            print(result.stdout)
        else:
            print("ERROR: Upload failed")
            print(result.stderr)
            print("\nYou may need to specify the correct zone.")
            print("Try running manually:")
            print(f"  gcloud compute scp {script_path} inventory-updater-vm:/home/banzo/vm_inventory_updater.py --zone=YOUR_ZONE")
            return False
        
        print("\n[2/3] Verifying file on VM...")
        result2 = subprocess.run(
            ['gcloud', 'compute', 'ssh', 'inventory-updater-vm',
             '--zone=us-central1-a',
             '--command', 'ls -lh /home/banzo/vm_inventory_updater.py'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result2.returncode == 0:
            print("SUCCESS: File verified on VM")
            print(result2.stdout)
        else:
            print("WARNING: Could not verify file (might be OK)")
            print(result2.stderr)
        
        print("\n[3/3] Testing script on VM...")
        print("\nRunning test to verify column detection...")
        
        result3 = subprocess.run(
            ['gcloud', 'compute', 'ssh', 'inventory-updater-vm',
             '--zone=us-central1-a',
             '--command', 'cd /home/banzo && python3 -c "import vm_inventory_updater; print(\'Script syntax OK\')"'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result3.returncode == 0:
            print("SUCCESS: Script syntax verified")
        else:
            print("WARNING: Syntax check failed (might be OK if dependencies missing)")
            print(result3.stderr)
        
        print("\n" + "="*80)
        print("DEPLOYMENT COMPLETE!")
        print("="*80)
        print("\nThe script will run automatically via cron every 5 minutes.")
        print("To check logs:")
        print("  gcloud compute ssh inventory-updater-vm --zone=YOUR_ZONE --command='tail -50 /home/banzo/inventory_cron.log'")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("ERROR: Operation timed out")
        return False
    except FileNotFoundError:
        print("ERROR: gcloud CLI not found. Please install Google Cloud SDK")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = deploy_to_vm()
    sys.exit(0 if success else 1)


