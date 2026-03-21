#!/usr/bin/env python3
"""
Deploy using gcloud commands via subprocess
"""

import subprocess
import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def run_gcloud_scp(local_file, remote_path):
    """Run gcloud compute scp"""
    # Try full path first, then fallback to PATH
    gcloud_paths = [
        r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "gcloud"
    ]
    
    gcloud_cmd = None
    for path in gcloud_paths:
        if os.path.exists(path) or path == "gcloud":
            gcloud_cmd = path
            break
    
    if not gcloud_cmd:
        print("   [FAIL] gcloud not found")
        return False
    
    cmd = [
        gcloud_cmd, "compute", "scp",
        local_file,
        f"banzo@real-time-inventory:{remote_path}",
        "--zone=us-central1-a",
        "--project=boxwood-chassis-332307"
    ]
    
    print(f"\n[UPLOAD] Uploading {os.path.basename(local_file)}...")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print(f"   ✅ Success!")
            if result.stdout:
                print(f"   {result.stdout.strip()}")
            return True
        else:
            print(f"   ❌ Failed (exit code {result.returncode})")
            if result.stderr:
                print(f"   Error: {result.stderr[:500]}")
            return False
            
    except FileNotFoundError:
        print("   [FAIL] gcloud not found in PATH")
        return False
    except subprocess.TimeoutExpired:
        print("   [FAIL] Command timed out")
        return False
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return False

def setup_cron():
    """Setup cron job"""
    cron_cmd = "(crontab -l 2>/dev/null | grep -v 'vm_inventory_updater.py'; echo '*/5 * * * * cd /home/banzo && /usr/bin/python3 /home/banzo/vm_inventory_updater.py >> /home/banzo/inventory_cron.log 2>&1') | crontab -"
    
    # Try full path first
    gcloud_paths = [
        r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "gcloud"
    ]
    
    gcloud_cmd = None
    for path in gcloud_paths:
        if os.path.exists(path) or path == "gcloud":
            gcloud_cmd = path
            break
    
    if not gcloud_cmd:
        print("   [FAIL] gcloud not found")
        return False
    
    cmd = [
        gcloud_cmd, "compute", "ssh",
        "real-time-inventory",
        "--zone=us-central1-a",
        "--project=boxwood-chassis-332307",
        "--command", cron_cmd
    ]
    
    print(f"\n[CRON] Setting up cron job...")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("   [OK] Cron job set!")
            return True
        else:
            print(f"   [WARN] Cron setup had issues (exit code {result.returncode})")
            if result.stderr:
                print(f"   {result.stderr[:300]}")
            return False
            
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return False

def main():
    print("="*80)
    print("DEPLOYING TO VM VIA GCLOUD")
    print("="*80)
    
    files_to_deploy = [
        ("vm_inventory_updater_fixed.py", "/home/banzo/vm_inventory_updater.py"),
        ("clover_creds.json", "/home/banzo/clover_creds.json"),
        ("service-account-key.json", "/home/banzo/service-account-key.json")
    ]
    
    # Check files exist
    for local_file, _ in files_to_deploy:
        if not os.path.exists(local_file):
            print(f"[FAIL] File not found: {local_file}")
            return False
    
    # Deploy files
    success_count = 0
    for local_file, remote_path in files_to_deploy:
        if run_gcloud_scp(local_file, remote_path):
            success_count += 1
    
    if success_count == len(files_to_deploy):
        print("\n[OK] All files deployed!")
        setup_cron()
        print("\n" + "="*80)
        print("[OK] DEPLOYMENT COMPLETE")
        print("="*80)
        return True
    else:
        print(f"\n[WARN] Only {success_count}/{len(files_to_deploy)} files deployed")
        print("\nThis is the VM-specific issue - API and gcloud both failing.")
        print("Try running gcloud commands manually in your terminal.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
