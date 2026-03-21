#!/usr/bin/env python3
"""
Run deployment using gcloud with service account auth
"""

import os
import sys
import subprocess
import tempfile

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

SERVICE_ACCOUNT_FILE = "service-account-key.json"
PROJECT_ID = "boxwood-chassis-332307"
ZONE = "us-central1-a"
VM_NAME = "real-time-inventory"

def run_deployment():
    """Run deployment using gcloud with service account"""
    print("="*80)
    print("RUNNING DEPLOYMENT WITH GCLOUD AUTH")
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
    
    # Create temp config directory
    temp_config = tempfile.mkdtemp()
    print(f"✅ Using temp config: {temp_config}")
    
    try:
        # Set environment
        env = os.environ.copy()
        env['CLOUDSDK_CONFIG'] = temp_config
        env['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath(SERVICE_ACCOUNT_FILE)
        
        # Activate service account
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
        
        if result.returncode != 0:
            print(f"⚠️  Auth activation: {result.stderr[:200]}")
        
        # Set project
        print("\n[2/3] Setting project...")
        subprocess.run(
            [gcloud_cmd, 'config', 'set', 'project', PROJECT_ID, '--quiet'],
            env=env,
            capture_output=True,
            timeout=30
        )
        
        # Execute deployment
        print("\n[3/3] Executing deployment on VM...")
        deploy_cmd = "curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-and-setup | bash"
        
        result = subprocess.run(
            [gcloud_cmd, 'compute', 'ssh', VM_NAME,
             '--zone', ZONE,
             '--project', PROJECT_ID,
             '--command', deploy_cmd,
             '--quiet'],
            env=env,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            print("✅ Deployment executed successfully!")
            print(result.stdout)
            return True
        else:
            print("⚠️  Deployment had issues:")
            print(result.stderr)
            if result.stdout:
                print("Output:")
                print(result.stdout)
            return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = run_deployment()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
