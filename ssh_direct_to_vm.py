#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH directly to VM using Python, bypassing gcloud issues
"""

import subprocess
import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

VM_NAME = "inventory-updater-vm"
VM_ZONE = "us-central1-a"

def get_vm_ip():
    """Get VM external IP using Compute Engine API"""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from google_auth_httplib2 import AuthorizedHttp
        import httplib2
        
        creds = service_account.Credentials.from_service_account_file(
            "service-account-key.json",
            scopes=['https://www.googleapis.com/auth/compute']
        )
        http = httplib2.Http(proxy_info=None)
        authorized_http = AuthorizedHttp(creds, http=http)
        compute = build('compute', 'v1', http=authorized_http)
        
        instance = compute.instances().get(
            project='boxwood-chassis-332307',
            zone=VM_ZONE,
            instance=VM_NAME
        ).execute()
        
        network_interfaces = instance.get('networkInterfaces', [])
        if network_interfaces:
            access_configs = network_interfaces[0].get('accessConfigs', [])
            if access_configs:
                return access_configs[0].get('natIP')
    except Exception as e:
        print(f"Could not get IP via API: {e}")
    return None

def execute_via_gcloud_direct():
    """Execute command using gcloud with clean environment"""
    print("="*80)
    print("EXECUTING VM FIX DIRECTLY")
    print("="*80)
    print()
    
    # Find gcloud
    gcloud_path = r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    if not os.path.exists(gcloud_path):
        gcloud_path = 'gcloud'
    
    # Clean environment
    env = os.environ.copy()
    
    # Remove problematic env vars
    for key in list(env.keys()):
        if 'PATH' in key.upper() and key != 'PATH':
            del env[key]
    
    # Set service account
    env['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath('service-account-key.json')
    
    # Try to use a temp config directory
    import tempfile
    temp_config = tempfile.mkdtemp()
    env['CLOUDSDK_CONFIG'] = temp_config
    
    try:
        print("Executing fix script on VM...")
        result = subprocess.run(
            [gcloud_path, 'compute', 'ssh', VM_NAME,
             '--zone', VM_ZONE,
             '--command', 'cd /home/banzo && python3 apply_fix_on_vm.py'],
            env=env,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print("\n✅ Fix executed successfully!")
            
            # Verify
            print("\nVerifying fix...")
            verify_result = subprocess.run(
                [gcloud_path, 'compute', 'ssh', VM_NAME,
                 '--zone', VM_ZONE,
                 '--command', "grep -A 5 'FIX FOR PROMOTION ITEMS' /home/banzo/vm_inventory_updater.py"],
                env=env,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            print(verify_result.stdout)
            return True
        else:
            print(f"\n❌ Command failed with exit code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        # Cleanup
        import shutil
        try:
            shutil.rmtree(temp_config, ignore_errors=True)
        except:
            pass

if __name__ == "__main__":
    success = execute_via_gcloud_direct()
    sys.exit(0 if success else 1)
