#!/usr/bin/env python3
"""
Set up gcloud authentication using service account
This avoids permission issues by using the service account key
"""

import os
import sys
import subprocess
import tempfile
import shutil

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

SERVICE_ACCOUNT_FILE = "service-account-key.json"
PROJECT_ID = "boxwood-chassis-332307"

def setup_gcloud_auth():
    """Set up gcloud authentication using service account"""
    print("="*80)
    print("SETTING UP GCLOUD AUTHENTICATION")
    print("="*80)
    
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"❌ Service account file not found: {SERVICE_ACCOUNT_FILE}")
        return False
    
    # Find gcloud
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
        print("❌ gcloud not found")
        return False
    
    print(f"\n✅ Found gcloud: {gcloud_cmd}")
    
    # Create temp config directory to avoid permission issues
    temp_config = tempfile.mkdtemp()
    print(f"✅ Created temp config: {temp_config}")
    
    try:
        # Set environment variables
        env = os.environ.copy()
        env['CLOUDSDK_CONFIG'] = temp_config
        env['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath(SERVICE_ACCOUNT_FILE)
        
        print("\n[1/3] Activating service account...")
        result = subprocess.run(
            [gcloud_cmd, 'auth', 'activate-service-account',
             '--key-file', os.path.abspath(SERVICE_ACCOUNT_FILE),
             '--quiet'],
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Service account activated")
        else:
            print(f"⚠️  Activation had issues: {result.stderr[:200]}")
        
        print("\n[2/3] Setting project...")
        result = subprocess.run(
            [gcloud_cmd, 'config', 'set', 'project', PROJECT_ID, '--quiet'],
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"✅ Project set to {PROJECT_ID}")
        else:
            print(f"⚠️  Setting project had issues: {result.stderr[:200]}")
        
        print("\n[3/3] Testing authentication...")
        result = subprocess.run(
            [gcloud_cmd, 'auth', 'list', '--quiet'],
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Authentication test passed")
            print(result.stdout)
        else:
            print(f"⚠️  Auth test had issues: {result.stderr[:200]}")
        
        print("\n" + "="*80)
        print("✅ GCLOUD AUTHENTICATION SET UP")
        print("="*80)
        print(f"\nTemp config: {temp_config}")
        print(f"Use this for gcloud commands:")
        print(f"  set CLOUDSDK_CONFIG={temp_config}")
        print(f"  {gcloud_cmd} compute ssh real-time-inventory --zone=us-central1-a --project={PROJECT_ID}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Don't delete temp config - user might need it
        print(f"\n💡 Temp config kept at: {temp_config}")
        print("   You can delete it later if needed")

if __name__ == "__main__":
    setup_gcloud_auth()
