#!/usr/bin/env python3
"""
Test if we can SSH to VM using service account
Try multiple methods: OS Login API, programmatic SSH, etc.
"""

import os
import sys

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2
import subprocess

def test_ssh_methods():
    """Test different methods to SSH/execute commands"""
    print("="*80)
    print("TESTING SSH ACCESS METHODS")
    print("="*80)
    
    service_account_path = "service-account-key.json"
    
    if not os.path.exists(service_account_path):
        print(f"ERROR: {service_account_path} not found!")
        return False
    
    print(f"\n[1/4] Authenticating...")
    try:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path,
            scopes=[
                'https://www.googleapis.com/auth/cloud-platform',
                'https://www.googleapis.com/auth/compute',
                'https://www.googleapis.com/auth/cloud-platform.read-only'
            ]
        )
        
        http = httplib2.Http(proxy_info=None)
        authorized_http = AuthorizedHttp(credentials, http=http)
        compute = build('compute', 'v1', http=authorized_http)
        print("   [OK] Authenticated")
    except Exception as e:
        print(f"   [ERROR] {e}")
        return False
    
    project = "boxwood-chassis-332307"
    zone = "us-central1-a"
    instance = "inventory-updater-vm"
    
    print(f"\n[2/4] Testing Method 1: OS Login API...")
    try:
        # Try OS Login API
        from google.cloud import oslogin
        oslogin_client = oslogin.OsLoginServiceClient(credentials=credentials)
        print("   [OK] OS Login client created")
        print("   [INFO] Can potentially use OS Login for SSH")
    except ImportError:
        print("   [INFO] google-cloud-os-login not installed")
        print("   [INFO] Install: pip install google-cloud-os-login")
    except Exception as e:
        print(f"   [INFO] {e}")
    
    print(f"\n[3/4] Testing Method 2: Serial Console Output...")
    try:
        # Try to read serial console (read-only, but shows if we can access)
        result = compute.instances().getSerialPortOutput(
            project=project,
            zone=zone,
            instance=instance,
            port=1
        ).execute()
        
        if result.get('contents'):
            print("   [OK] Can read serial console output")
            print(f"   [INFO] Last {len(result.get('contents', ''))} chars of serial output")
        else:
            print("   [INFO] Serial console empty or not enabled")
    except Exception as e:
        print(f"   [INFO] Serial console: {e}")
    
    print(f"\n[4/4] Testing Method 3: gcloud CLI with service account...")
    try:
        gcloud_path = r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
        
        if os.path.exists(gcloud_path):
            print(f"   [OK] gcloud found at: {gcloud_path}")
            
            # Try to authenticate with service account
            env = os.environ.copy()
            env['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath(service_account_path)
            
            auth_result = subprocess.run(
                [gcloud_path, 'auth', 'activate-service-account',
                 '--key-file', os.path.abspath(service_account_path),
                 '--quiet'],
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if auth_result.returncode == 0:
                print("   [OK] Service account authenticated with gcloud")
                
                # Try to SSH (this will likely fail due to SSH key issues)
                print("   [INFO] Attempting SSH connection...")
                ssh_result = subprocess.run(
                    [gcloud_path, 'compute', 'ssh', instance,
                     '--zone', zone,
                     '--command', 'echo "SSH test successful"'],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if ssh_result.returncode == 0:
                    print("   [SUCCESS] SSH works!")
                    print(f"   Output: {ssh_result.stdout}")
                    return True
                else:
                    print(f"   [INFO] SSH failed (expected): {ssh_result.stderr[:200]}")
            else:
                print(f"   [INFO] Auth failed: {auth_result.stderr[:200]}")
        else:
            print(f"   [INFO] gcloud not found at expected path")
    except Exception as e:
        print(f"   [INFO] gcloud test: {e}")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("\nDirect SSH via API: Not available (need SSH)")
    print("OS Login API: Possible (need to install library)")
    print("Serial Console: Read-only (can't execute commands)")
    print("gcloud CLI: Has permission issues (SSH keys)")
    print("\nBest option: Use Google Cloud Console SSH (browser-based)")
    
    return False

if __name__ == "__main__":
    test_ssh_methods()
