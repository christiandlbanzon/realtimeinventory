#!/usr/bin/env python3
"""
Simple VM check using Python API + gcloud SSH
"""
import subprocess
import os
import tempfile
import shutil

# Get gcloud path
GCLOUD_PATH = r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
if not os.path.exists(GCLOUD_PATH):
    GCLOUD_PATH = 'gcloud'

TEMP_CONFIG = tempfile.mkdtemp()

def get_env():
    env = os.environ.copy()
    env['CLOUDSDK_CONFIG'] = TEMP_CONFIG
    env['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath('service-account-key.json')
    for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
        env.pop(proxy_var, None)
    return env

def check_vm_via_api():
    """Check VM status via Python API"""
    print("="*80)
    print("VM STATUS (via Python API)")
    print("="*80)
    
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from google_auth_httplib2 import AuthorizedHttp
        import httplib2
        
        credentials = service_account.Credentials.from_service_account_file(
            'service-account-key.json',
            scopes=['https://www.googleapis.com/auth/compute']
        )
        
        http = httplib2.Http(proxy_info=None)
        authorized_http = AuthorizedHttp(credentials, http=http)
        compute = build('compute', 'v1', http=authorized_http)
        
        instance_info = compute.instances().get(
            project='boxwood-chassis-332307',
            zone='us-central1-a',
            instance='inventory-updater-vm'
        ).execute()
        
        status = instance_info.get('status')
        print(f"[OK] VM Status: {status}")
        return status == 'RUNNING'
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def check_code_on_vm():
    """Check if fixes are on VM"""
    print("\n" + "="*80)
    print("CHECKING CODE ON VM")
    print("="*80)
    
    env = get_env()
    
    # Check for San Patricio fix
    print("\n[1] Checking San Patricio fix...")
    result = subprocess.run(
        [GCLOUD_PATH, 'compute', 'ssh', 'inventory-updater-vm',
         '--zone=us-central1-a',
         '--command', 'grep -c "Only use fallback if API actually failed" /home/banzo/vm_inventory_updater.py'],
        env=env,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode == 0 and result.stdout.strip() and result.stdout.strip() != '0':
        print("[OK] San Patricio fix found!")
    else:
        print("[MISSING] San Patricio fix not found")
        print(f"   Output: {result.stdout.strip()}")
        print(f"   Error: {result.stderr[:200]}")
    
    # Check for validation fix
    print("\n[2] Checking validation fix...")
    result = subprocess.run(
        [GCLOUD_PATH, 'compute', 'ssh', 'inventory-updater-vm',
         '--zone=us-central1-a',
         '--command', 'grep -c "LARGE DISCREPANCY DETECTED" /home/banzo/vm_inventory_updater.py'],
        env=env,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode == 0 and result.stdout.strip() and result.stdout.strip() != '0':
        print("[OK] Validation fix found!")
    else:
        print("[MISSING] Validation fix not found")
        print(f"   Output: {result.stdout.strip()}")
        print(f"   Error: {result.stderr[:200]}")
    
    # Get file info
    print("\n[3] File info...")
    result = subprocess.run(
        [GCLOUD_PATH, 'compute', 'ssh', 'inventory-updater-vm',
         '--zone=us-central1-a',
         '--command', 'ls -lh /home/banzo/vm_inventory_updater.py'],
        env=env,
        capture_output=True,
        text=True,
        timeout=30
    )
    if result.returncode == 0:
        print(f"   {result.stdout.strip()}")

def check_logs():
    """Check recent logs"""
    print("\n" + "="*80)
    print("CHECKING LOGS")
    print("="*80)
    
    env = get_env()
    
    # Check if log exists
    result = subprocess.run(
        [GCLOUD_PATH, 'compute', 'ssh', 'inventory-updater-vm',
         '--zone=us-central1-a',
         '--command', 'test -f /home/banzo/inventory_cron.log && echo "EXISTS" || echo "NOT_FOUND"'],
        env=env,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.stdout.strip() == "EXISTS":
        print("[OK] Log file exists")
        
        # Get last 30 lines
        print("\n[Last 30 lines of log:]")
        print("-"*80)
        result = subprocess.run(
            [GCLOUD_PATH, 'compute', 'ssh', 'inventory-updater-vm',
             '--zone=us-central1-a',
             '--command', 'tail -30 /home/banzo/inventory_cron.log'],
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print(result.stdout)
    else:
        print("[WARNING] Log file not found")
        print(f"   Output: {result.stdout.strip()}")

def main():
    print("\n" + "="*80)
    print("VM HEALTH CHECK")
    print("="*80)
    
    vm_ok = check_vm_via_api()
    check_code_on_vm()
    check_logs()
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"VM Status: {'[OK]' if vm_ok else '[ERROR]'}")
    
    try:
        shutil.rmtree(TEMP_CONFIG, ignore_errors=True)
    except:
        pass

if __name__ == "__main__":
    main()
