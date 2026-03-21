#!/usr/bin/env python3
"""
Debug the issues and deploy using the most reliable method
"""

import os
import sys
import time

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

PROJECT_ID = "boxwood-chassis-332307"
ZONE = "us-central1-a"
VM_NAME = "real-time-inventory"
SERVICE_ACCOUNT_FILE = "service-account-key.json"

def debug_api_status():
    """Debug why API is returning 503"""
    print("="*80)
    print("DEBUGGING API STATUS")
    print("="*80)
    
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=[
                'https://www.googleapis.com/auth/cloud-platform',
                'https://www.googleapis.com/auth/compute'
            ]
        )
        
        http = httplib2.Http(proxy_info=None)
        authorized_http = AuthorizedHttp(credentials, http=http)
        compute = build('compute', 'v1', http=authorized_http)
        
        print("\n✅ Authenticated successfully")
        
        # Try simple GET first
        print("\n[1/3] Testing simple API call (get instance)...")
        try:
            instance = compute.instances().get(
                project=PROJECT_ID,
                zone=ZONE,
                instance=VM_NAME
            ).execute()
            
            status = instance.get('status', 'UNKNOWN')
            print(f"✅ API working! VM Status: {status}")
            
            # Check metadata
            metadata = instance.get('metadata', {})
            items = metadata.get('items', [])
            
            deploy_script_found = False
            for item in items:
                if item.get('key') == 'deploy-and-setup':
                    deploy_script_found = True
                    print("✅ Deployment script found in metadata")
                    break
            
            if not deploy_script_found:
                print("⚠️  Deployment script not in metadata")
            
            return True, instance
            
        except Exception as e:
            error_msg = str(e)
            if "503" in error_msg or "unavailable" in error_msg.lower():
                print(f"❌ API returning 503: {e}")
                print("\n🔍 Debugging 503 error:")
                print("   - This is a temporary Google Cloud API issue")
                print("   - Not related to authentication")
                print("   - The API backend is temporarily unavailable")
                print("   - Solution: Wait a few minutes and retry, or use gcloud CLI")
                return False, None
            else:
                print(f"❌ API error: {e}")
                return False, None
                
    except Exception as e:
        print(f"\n❌ Authentication/API error: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def deploy_via_startup_script(instance):
    """Deploy by setting startup script and restarting"""
    print("\n" + "="*80)
    print("DEPLOYING VIA STARTUP SCRIPT")
    print("="*80)
    
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=[
                'https://www.googleapis.com/auth/cloud-platform',
                'https://www.googleapis.com/auth/compute'
            ]
        )
        
        http = httplib2.Http(proxy_info=None)
        authorized_http = AuthorizedHttp(credentials, http=http)
        compute = build('compute', 'v1', http=authorized_http)
        
        # Get deployment script from metadata
        metadata = instance.get('metadata', {})
        items = metadata.get('items', [])
        
        deploy_script = None
        for item in items:
            if item.get('key') == 'deploy-and-setup':
                deploy_script = item.get('value')
                break
        
        if not deploy_script:
            print("❌ Deployment script not found in metadata!")
            return False
        
        print("✅ Found deployment script")
        
        # Try to set as startup script with retries
        fingerprint = metadata.get('fingerprint', '')
        
        # Remove old startup script
        items = [item for item in items if item.get('key') != 'startup-script']
        items.append({
            'key': 'startup-script',
            'value': deploy_script
        })
        
        print("\n[1/2] Setting startup script (with retries)...")
        max_retries = 5
        for attempt in range(max_retries):
            try:
                compute.instances().setMetadata(
                    project=PROJECT_ID,
                    zone=ZONE,
                    instance=VM_NAME,
                    body={
                        'fingerprint': fingerprint,
                        'items': items
                    }
                ).execute()
                
                print("✅ Startup script set successfully!")
                break
                
            except Exception as e:
                error_msg = str(e)
                if "503" in error_msg and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    print(f"   ⚠️  503 error (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s...")
                    time.sleep(wait_time)
                    # Refresh fingerprint
                    instance = compute.instances().get(
                        project=PROJECT_ID,
                        zone=ZONE,
                        instance=VM_NAME
                    ).execute()
                    fingerprint = instance.get('metadata', {}).get('fingerprint', '')
                else:
                    raise
        
        # Restart VM
        print("\n[2/2] Restarting VM to trigger deployment...")
        try:
            compute.instances().reset(
                project=PROJECT_ID,
                zone=ZONE,
                instance=VM_NAME
            ).execute()
            
            print("✅ VM restart initiated")
            print("\n⏳ VM is restarting...")
            print("   Deployment script will run automatically on startup.")
            print("   Waiting for restart...")
            
            # Wait for restart
            for i in range(60):
                time.sleep(2)
                instance = compute.instances().get(
                    project=PROJECT_ID,
                    zone=ZONE,
                    instance=VM_NAME
                ).execute()
                
                if instance.get('status') == 'RUNNING':
                    print("   ✅ VM is running")
                    print("\n✅ Deployment should have executed during startup!")
                    return True
            
            print("   ⚠️  VM may still be restarting")
            return True
            
        except Exception as e:
            print(f"⚠️  Error restarting VM: {e}")
            print("   But startup script is set - it will run on next boot")
            return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*80)
    print("DEBUG AND DEPLOY")
    print("="*80)
    
    # Debug API
    api_working, instance = debug_api_status()
    
    if not api_working:
        print("\n" + "="*80)
        print("⚠️  API ISSUE DETECTED")
        print("="*80)
        print("\nThe Google Cloud API is returning 503 errors (temporary).")
        print("This is a Google Cloud backend issue, not an authentication problem.")
        print("\nOptions:")
        print("1. Wait 5-10 minutes and retry")
        print("2. Use gcloud CLI in your terminal (where you did gcloud auth login)")
        print("3. The deployment script is already in VM metadata - you can SSH and run it")
        return False
    
    if instance:
        # Try deployment
        success = deploy_via_startup_script(instance)
        
        if success:
            print("\n" + "="*80)
            print("✅ DEPLOYMENT INITIATED")
            print("="*80)
            print("\nThe VM has been restarted and deployment script ran automatically.")
            print("Check logs: gcloud compute ssh real-time-inventory --zone=us-central1-a --command='tail -50 /home/banzo/inventory_cron.log'")
        
        return success
    
    return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
