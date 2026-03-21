#!/usr/bin/env python3
"""
Deploy the Biscoff fix to VM using Compute Engine API
"""

import os
import sys
import re

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
VM_NAME = "inventory-updater-vm"
SERVICE_ACCOUNT_FILE = "service-account-key.json"

def extract_python_code():
    """Extract Python code from deploy_temp.sh"""
    print("="*80)
    print("EXTRACTING PYTHON CODE")
    print("="*80)
    
    with open('deploy_temp.sh', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find Python code between 'ENDOFFILE' markers
    pattern = r"cat > vm_inventory_updater.py << 'ENDOFFILE'\n(.*?)\nENDOFFILE"
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        python_code = match.group(1)
        print(f"✅ Extracted {len(python_code)} characters")
        
        # Verify fix is present
        if '"*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff"' in python_code:
            print("✅ Biscoff fix verified in code")
        else:
            print("❌ WARNING: Biscoff fix not found!")
            return None
        
        return python_code
    else:
        print("❌ Could not extract Python code")
        return None

def deploy_via_metadata(compute, python_code):
    """Deploy Python code to VM via metadata startup script"""
    print("\n" + "="*80)
    print("DEPLOYING VIA METADATA")
    print("="*80)
    
    try:
        # Get current instance info
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        # Get current metadata
        metadata = instance.get('metadata', {})
        fingerprint = metadata.get('fingerprint', '')
        items = metadata.get('items', [])
        
        # Remove old startup scripts
        items = [item for item in items if item.get('key') not in ['startup-script', 'deploy-script']]
        
        # Create deployment script
        deploy_script = f"""#!/bin/bash
cd /home/banzo

# Backup current file
if [ -f vm_inventory_updater.py ]; then
    cp vm_inventory_updater.py vm_inventory_updater.py.backup.$(date +%Y%m%d_%H%M%S)
fi

# Write new file
cat > vm_inventory_updater.py << 'PYTHONEOF'
{python_code}
PYTHONEOF

# Set permissions
chmod +x vm_inventory_updater.py

# Log deployment
echo "$(date): Biscoff fix deployed" >> /home/banzo/deployment.log
"""
        
        # Add deployment script to metadata
        items.append({
            'key': 'deploy-biscoff-fix',
            'value': deploy_script
        })
        
        # Update metadata
        compute.instances().setMetadata(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME,
            body={
                'fingerprint': fingerprint,
                'items': items
            }
        ).execute()
        
        print("✅ Metadata updated")
        print("\n⚠️  Note: The VM needs to be restarted for the metadata script to run.")
        print("   OR you can SSH and run the script manually:")
        print(f"   gcloud compute ssh {VM_NAME} --zone={ZONE}")
        print("   Then run: curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-biscoff-fix | bash")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def deploy_via_ssh_command(compute, python_code):
    """Deploy by creating a command to write the file directly"""
    print("\n" + "="*80)
    print("DEPLOYMENT INSTRUCTIONS")
    print("="*80)
    
    # Save Python code to local file
    temp_file = "vm_inventory_updater_fixed.py"
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(python_code)
    
    print(f"✅ Created local file: {temp_file}")
    print(f"\nTo deploy, run this command:")
    print(f"\n  gcloud compute scp {temp_file} {VM_NAME}:{VM_NAME}:/home/banzo/vm_inventory_updater.py --zone={ZONE}")
    print(f"\nOr use the service account credentials:")
    print(f"\n  gcloud compute scp --zone={ZONE} {temp_file} {VM_NAME}:/home/banzo/vm_inventory_updater.py")
    
    # Try to get VM IP for direct SSH
    try:
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        network_interfaces = instance.get('networkInterfaces', [])
        if network_interfaces:
            access_configs = network_interfaces[0].get('accessConfigs', [])
            if access_configs:
                external_ip = access_configs[0].get('natIP')
                if external_ip:
                    print(f"\nVM External IP: {external_ip}")
                    print(f"You can also use:")
                    print(f"  scp {temp_file} banzo@{external_ip}:/home/banzo/vm_inventory_updater.py")
    except:
        pass
    
    return temp_file

def main():
    """Main function"""
    print("="*80)
    print("DEPLOY BISCOFF FIX TO VM")
    print("="*80)
    
    # Extract Python code
    python_code = extract_python_code()
    if not python_code:
        return False
    
    # Authenticate
    print("\n" + "="*80)
    print("AUTHENTICATING")
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
        
        print("✅ Authenticated")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False
    
    # Deploy via metadata (requires VM restart) or provide instructions
    print("\n" + "="*80)
    print("CHOOSING DEPLOYMENT METHOD")
    print("="*80)
    
    # Method 1: Create local file and provide instructions
    temp_file = deploy_via_ssh_command(compute, python_code)
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"\n✅ Python code extracted and verified")
    print(f"✅ Local file created: {temp_file}")
    print(f"\n📋 Next Steps:")
    print(f"   1. Use gcloud to copy the file to VM:")
    print(f"      gcloud compute scp {temp_file} {VM_NAME}:/home/banzo/vm_inventory_updater.py --zone={ZONE}")
    print(f"\n   2. Or use the access script we created earlier:")
    print(f"      python access_vm_with_service_account.py")
    print(f"      Then manually copy the file")
    print(f"\n   3. After deployment, the cron job will use the new code on next run")
    print(f"      (runs every 5 minutes)")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
