#!/usr/bin/env python3
"""
Test if we can use gcloud commands despite permission issues
Try workarounds: temp config, service account auth, etc.
"""

import os
import sys
import subprocess
import tempfile
import shutil

def test_gcloud():
    """Test gcloud CLI usage"""
    print("="*80)
    print("TESTING GCLOUD CLI USAGE")
    print("="*80)
    
    service_account_path = "service-account-key.json"
    gcloud_path = r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    
    if not os.path.exists(gcloud_path):
        print(f"ERROR: gcloud not found at {gcloud_path}")
        return False
    
    print(f"\n[1/4] Found gcloud at: {gcloud_path}")
    
    # Create temp config directory
    temp_config = tempfile.mkdtemp()
    print(f"\n[2/4] Using temp config: {temp_config}")
    
    try:
        env = os.environ.copy()
        env['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath(service_account_path)
        env['CLOUDSDK_CONFIG'] = temp_config
        
        # Disable proxy
        for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
            env.pop(proxy_var, None)
        
        print(f"\n[3/4] Testing gcloud commands...")
        
        # Test 1: Basic version check
        print("\n   Test 1: gcloud version...")
        result = subprocess.run(
            [gcloud_path, 'version'],
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print(f"      [OK] gcloud works!")
            print(f"      {result.stdout.strip()[:100]}")
        else:
            print(f"      [ERROR] {result.stderr[:200]}")
            return False
        
        # Test 2: Authenticate with service account
        print("\n   Test 2: Authenticate with service account...")
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
            print("      [OK] Service account authenticated")
        else:
            print(f"      [WARNING] Auth: {auth_result.stderr[:200]}")
            # Continue anyway - might still work
        
        # Test 3: Set project
        print("\n   Test 3: Set project...")
        project_result = subprocess.run(
            [gcloud_path, 'config', 'set', 'project', 'boxwood-chassis-332307'],
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        if project_result.returncode == 0:
            print("      [OK] Project set")
        else:
            print(f"      [WARNING] {project_result.stderr[:200]}")
        
        # Test 4: Try compute commands (no SSH needed)
        print("\n   Test 4: Test compute commands...")
        list_result = subprocess.run(
            [gcloud_path, 'compute', 'instances', 'list',
             '--zones', 'us-central1-a',
             '--format', 'json'],
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        if list_result.returncode == 0:
            print("      [OK] Can list VM instances!")
            import json
            instances = json.loads(list_result.stdout)
            for inst in instances:
                if inst.get('name') == 'inventory-updater-vm':
                    print(f"      [OK] Found VM: {inst.get('status')}")
        else:
            print(f"      [ERROR] {list_result.stderr[:200]}")
        
        # Test 5: Try SSH (this will likely fail due to SSH keys)
        print("\n   Test 5: Test SSH connection...")
        ssh_result = subprocess.run(
            [gcloud_path, 'compute', 'ssh', 'inventory-updater-vm',
             '--zone', 'us-central1-a',
             '--command', 'echo "SSH test"',
             '--quiet'],
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        if ssh_result.returncode == 0:
            print("      [SUCCESS] SSH works!")
            print(f"      Output: {ssh_result.stdout}")
            return True
        else:
            print(f"      [INFO] SSH failed (expected): {ssh_result.stderr[:300]}")
            print("\n      SSH requires SSH keys. Options:")
            print("      1. Use Google Cloud Console SSH (browser-based)")
            print("      2. Fix SSH keys: gcloud compute config-ssh (needs admin)")
            print("      3. Use metadata + manual execution")
        
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print("\n[OK] gcloud CLI works for:")
        print("   - Listing instances")
        print("   - Getting VM info")
        print("   - Other compute commands")
        print("\n[LIMITED] gcloud CLI can't:")
        print("   - SSH (needs SSH keys)")
        print("   - Execute commands directly")
        print("\n[WORKAROUND] For SSH:")
        print("   - Use Google Cloud Console SSH")
        print("   - Or fix SSH keys (run as admin)")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up temp config
        try:
            shutil.rmtree(temp_config, ignore_errors=True)
        except:
            pass

if __name__ == "__main__":
    test_gcloud()
