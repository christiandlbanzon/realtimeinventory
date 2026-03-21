#!/usr/bin/env python3
"""
Access VM using service account credentials
"""

import os
import sys

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
import json

# VM Configuration
PROJECT_ID = "boxwood-chassis-332307"
ZONE = "us-central1-a"
VM_NAME = "inventory-updater-vm"
SERVICE_ACCOUNT_FILE = "service-account-key.json"

def authenticate():
    """Authenticate using service account"""
    print("="*80)
    print("AUTHENTICATING WITH SERVICE ACCOUNT")
    print("="*80)
    
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"❌ ERROR: {SERVICE_ACCOUNT_FILE} not found!")
        return None
    
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=[
                'https://www.googleapis.com/auth/cloud-platform',
                'https://www.googleapis.com/auth/compute',
                'https://www.googleapis.com/auth/compute.readonly'
            ]
        )
        
        http = httplib2.Http(proxy_info=None)
        authorized_http = AuthorizedHttp(credentials, http=http)
        compute = build('compute', 'v1', http=authorized_http)
        
        print(f"✅ Authenticated successfully!")
        print(f"   Service Account: {credentials.service_account_email}")
        print(f"   Project ID: {PROJECT_ID}")
        return compute
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return None

def get_vm_info(compute):
    """Get VM instance information"""
    print("\n" + "="*80)
    print("GETTING VM INFORMATION")
    print("="*80)
    
    try:
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        print(f"\n✅ VM Found: {VM_NAME}")
        print(f"\n📋 Instance Details:")
        print(f"   Status: {instance.get('status', 'UNKNOWN')}")
        print(f"   Machine Type: {instance.get('machineType', '').split('/')[-1]}")
        print(f"   Zone: {instance.get('zone', '').split('/')[-1]}")
        
        # Network Information
        network_interfaces = instance.get('networkInterfaces', [])
        if network_interfaces:
            print(f"\n🌐 Network Information:")
            for i, ni in enumerate(network_interfaces):
                print(f"   Interface {i+1}:")
                print(f"     Network: {ni.get('network', '').split('/')[-1]}")
                print(f"     Internal IP: {ni.get('networkIP', 'N/A')}")
                
                access_configs = ni.get('accessConfigs', [])
                if access_configs:
                    for ac in access_configs:
                        external_ip = ac.get('natIP', 'N/A')
                        print(f"     External IP: {external_ip}")
                        if external_ip != 'N/A':
                            print(f"     ✅ VM has external IP: {external_ip}")
                else:
                    print(f"     ⚠️  No external IP configured")
        
        # Metadata
        metadata = instance.get('metadata', {})
        if metadata:
            print(f"\n📝 Metadata:")
            items = metadata.get('items', [])
            for item in items[:5]:  # Show first 5 items
                key = item.get('key', '')
                value = item.get('value', '')[:50]  # Truncate long values
                print(f"   {key}: {value}")
            if len(items) > 5:
                print(f"   ... and {len(items) - 5} more items")
        
        # Service Accounts
        service_accounts = instance.get('serviceAccounts', [])
        if service_accounts:
            print(f"\n🔐 Service Accounts:")
            for sa in service_accounts:
                print(f"   Email: {sa.get('email', 'N/A')}")
                scopes = sa.get('scopes', [])
                if scopes:
                    print(f"   Scopes: {len(scopes)} scopes configured")
        
        return instance
        
    except Exception as e:
        print(f"❌ Failed to get VM info: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_vm_access(compute):
    """Check if we can access VM via different methods"""
    print("\n" + "="*80)
    print("CHECKING VM ACCESS METHODS")
    print("="*80)
    
    # Method 1: Serial Port Output (always available)
    print("\n[1/3] Testing Serial Port Access...")
    try:
        result = compute.instances().getSerialPortOutput(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        output = result.get('contents', '')
        if output:
            print("   ✅ Can access serial port output")
            # Show last few lines
            lines = output.split('\n')[-10:]
            print(f"   Last {len(lines)} lines of serial output:")
            for line in lines:
                if line.strip():
                    print(f"      {line[:80]}")
        else:
            print("   ⚠️  Serial port output is empty")
    except Exception as e:
        print(f"   ❌ Serial port access failed: {e}")
    
    # Method 2: Check if VM is running
    print("\n[2/3] Checking VM Status...")
    try:
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        status = instance.get('status', 'UNKNOWN')
        print(f"   VM Status: {status}")
        
        if status == 'RUNNING':
            print("   ✅ VM is running")
        elif status == 'STOPPED':
            print("   ⚠️  VM is stopped - start it to access")
        elif status == 'STOPPING':
            print("   ⚠️  VM is stopping")
        elif status == 'STARTING':
            print("   ⚠️  VM is starting")
        else:
            print(f"   ⚠️  VM status: {status}")
            
    except Exception as e:
        print(f"   ❌ Failed to check status: {e}")
    
    # Method 3: List available operations
    print("\n[3/3] Checking Available Operations...")
    try:
        # Try to list operations to verify permissions
        operations = compute.zoneOperations().list(
            project=PROJECT_ID,
            zone=ZONE,
            maxResults=1
        ).execute()
        
        print("   ✅ Can list operations (has compute permissions)")
        
    except Exception as e:
        print(f"   ⚠️  Cannot list operations: {e}")

def main():
    """Main function"""
    print("\n" + "="*80)
    print("VM ACCESS USING SERVICE ACCOUNT")
    print("="*80)
    print(f"Project: {PROJECT_ID}")
    print(f"Zone: {ZONE}")
    print(f"VM Name: {VM_NAME}")
    print(f"Service Account File: {SERVICE_ACCOUNT_FILE}")
    
    # Authenticate
    compute = authenticate()
    if not compute:
        print("\n❌ Cannot proceed without authentication")
        return False
    
    # Get VM info
    instance = get_vm_info(compute)
    if not instance:
        print("\n❌ Cannot proceed without VM info")
        return False
    
    # Check access methods
    check_vm_access(compute)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    status = instance.get('status', 'UNKNOWN')
    network_interfaces = instance.get('networkInterfaces', [])
    external_ip = None
    
    if network_interfaces:
        access_configs = network_interfaces[0].get('accessConfigs', [])
        if access_configs:
            external_ip = access_configs[0].get('natIP')
    
    print(f"\n✅ Authentication: SUCCESS")
    print(f"✅ VM Access: {'SUCCESS' if instance else 'FAILED'}")
    print(f"✅ VM Status: {status}")
    
    if external_ip:
        print(f"\n🌐 External IP: {external_ip}")
        print(f"\n💡 To SSH to the VM:")
        print(f"   ssh <username>@{external_ip}")
        print(f"\n💡 Or using gcloud:")
        print(f"   gcloud compute ssh {VM_NAME} --zone={ZONE}")
    else:
        print(f"\n⚠️  No external IP found")
        print(f"   The VM may not have external access configured")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
