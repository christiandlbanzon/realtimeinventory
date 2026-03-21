#!/usr/bin/env python3
"""
Create a new VM and deploy inventory updater with all necessary files
"""

import os
import sys
import base64
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
VM_NAME = "real-time-inventory"  # Updated to new name
SERVICE_ACCOUNT_FILE = "service-account-key.json"
VM_USER = "banzo"

# Files to deploy
FILES_TO_DEPLOY = {
    "vm_inventory_updater_fixed.py": "/home/banzo/vm_inventory_updater.py",
    "clover_creds.json": "/home/banzo/clover_creds.json",
    "service-account-key.json": "/home/banzo/service-account-key.json"
}

def create_vm(compute):
    """Create a new VM instance with automatic deployment"""
    print("="*80)
    print("CREATING NEW VM WITH AUTOMATIC DEPLOYMENT")
    print("="*80)
    print(f"\nVM Name: {VM_NAME}")
    print(f"Zone: {ZONE}")
    print(f"Project: {PROJECT_ID}")
    
    # Read files for deployment
    files_content = {}
    for local_file, remote_path in FILES_TO_DEPLOY.items():
        if not os.path.exists(local_file):
            print(f"⚠️  File not found: {local_file}")
            continue
        
        with open(local_file, 'r', encoding='utf-8') as f:
            content = f.read()
            files_content[remote_path] = {
                'content': content,
                'size': len(content)
            }
            print(f"✅ Read {local_file} ({len(content):,} bytes)")
    
    # Verify February sheet ID
    if files_content.get("/home/banzo/vm_inventory_updater.py"):
        if "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4" in files_content["/home/banzo/vm_inventory_updater.py"]['content']:
            print("✅ February sheet ID verified in code")
        else:
            print("⚠️  WARNING: February sheet ID not found in code!")
    
    # Check if VM already exists - delete it automatically
    try:
        existing = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        print(f"\n⚠️  VM '{VM_NAME}' already exists!")
        print("   Status:", existing.get('status'))
        print("   Deleting existing VM to recreate...")
        compute.instances().delete(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        print("   Waiting for deletion...")
        for i in range(30):
            time.sleep(2)
            try:
                compute.instances().get(
                    project=PROJECT_ID,
                    zone=ZONE,
                    instance=VM_NAME
                ).execute()
            except:
                print("   ✅ VM deleted")
                break
    except Exception as e:
        if "not found" not in str(e).lower():
            print(f"   Error checking VM: {e}")
            return False
        print("   ✅ VM doesn't exist, will create new one")
    
    # Build startup script with file deployment
    startup_script = f"""#!/bin/bash
set -e
exec > /var/log/startup.log 2>&1

echo "=== VM Startup Script ==="
date

# Update system
echo "Updating system..."
apt-get update -y
apt-get install -y python3 python3-pip git

# Create user if doesn't exist
if ! id -u {VM_USER} &>/dev/null; then
    useradd -m -s /bin/bash {VM_USER}
fi

# Create directory
mkdir -p /home/{VM_USER}
chown -R {VM_USER}:{VM_USER} /home/{VM_USER}

# Install Python packages
echo "Installing Python packages..."
pip3 install --upgrade pip
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests python-dotenv fuzzywuzzy python-Levenshtein

# Deploy files
echo "Deploying files..."
cd /home/{VM_USER}
"""
    
    # Add file deployment to startup script
    for remote_path, file_info in files_content.items():
        filename = os.path.basename(remote_path)
        content_b64 = base64.b64encode(file_info['content'].encode('utf-8')).decode('utf-8')
        startup_script += f"""
# Deploy {filename}
echo '{content_b64}' | base64 -d > {remote_path}
chmod 644 {remote_path}
"""
    
    # Make main script executable and set up cron
    startup_script += f"""
chmod +x /home/{VM_USER}/vm_inventory_updater.py

# Set up cron job
echo "Setting up cron job..."
(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/{VM_USER} && /usr/bin/python3 /home/{VM_USER}/vm_inventory_updater.py >> /home/{VM_USER}/inventory_cron.log 2>&1") | crontab -

echo "✅ Deployment complete!"
echo "Cron job configured:"
crontab -l
date
"""
    
    # VM configuration
    machine_type = f"zones/{ZONE}/machineTypes/e2-micro"  # Smallest/cheapest
    
    config = {
        'name': VM_NAME,
        'machineType': machine_type,
        'disks': [{
            'boot': True,
            'autoDelete': True,
            'initializeParams': {
                'sourceImage': 'projects/debian-cloud/global/images/family/debian-12',
                'diskSizeGb': '20'
            }
        }],
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [{
                'type': 'ONE_TO_ONE_NAT',
                'name': 'External NAT'
            }]
        }],
        'serviceAccounts': [{
            'email': 'default',
            'scopes': [
                'https://www.googleapis.com/auth/cloud-platform',
                'https://www.googleapis.com/auth/spreadsheets'
            ]
        }],
        'metadata': {
            'items': [{
                'key': 'startup-script',
                'value': startup_script
            }]
        },
        'tags': {
            'items': ['inventory-updater']
        }
    }
    
    # Retry logic for API errors
    max_retries = 5
    for attempt in range(max_retries):
        try:
            print(f"\n[1/3] Creating VM... (attempt {attempt + 1}/{max_retries})")
            operation = compute.instances().insert(
                project=PROJECT_ID,
                zone=ZONE,
                body=config
            ).execute()
            break
        except Exception as e:
            if attempt < max_retries - 1 and ("503" in str(e) or "unavailable" in str(e).lower()):
                wait_time = (attempt + 1) * 5
                print(f"   ⚠️  API temporarily unavailable, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
    
    try:
        
        print("   ✅ VM creation initiated")
        print(f"   Operation: {operation['name']}")
        
        # Wait for VM to be created
        print("\n[2/3] Waiting for VM to be created...")
        for i in range(60):
            time.sleep(5)
            op = compute.zoneOperations().get(
                project=PROJECT_ID,
                zone=ZONE,
                operation=operation['name']
            ).execute()
            
            if op['status'] == 'DONE':
                if 'error' in op:
                    print(f"   ❌ Error: {op['error']}")
                    return False
                print("   ✅ VM created successfully!")
                break
        else:
            print("   ⚠️  VM creation taking longer than expected")
        
        # Wait for VM to start
        print("\n[3/3] Waiting for VM to start...")
        for i in range(30):
            time.sleep(2)
            instance = compute.instances().get(
                project=PROJECT_ID,
                zone=ZONE,
                instance=VM_NAME
            ).execute()
            
            if instance.get('status') == 'RUNNING':
                print("   ✅ VM is running")
                return True
        
        print("   ⚠️  VM may still be starting")
        return True
        
    except Exception as e:
        print(f"\n❌ Error creating VM: {e}")
        import traceback
        traceback.print_exc()
        return False

def deploy_files(compute):
    """Deploy files to VM via metadata"""
    print("\n" + "="*80)
    print("DEPLOYING FILES TO VM")
    print("="*80)
    
    # Read all files
    files_content = {}
    for local_file, remote_path in FILES_TO_DEPLOY.items():
        if not os.path.exists(local_file):
            print(f"⚠️  File not found: {local_file} (skipping)")
            continue
        
        with open(local_file, 'r', encoding='utf-8') as f:
            content = f.read()
            files_content[remote_path] = {
                'content': content,
                'size': len(content)
            }
            print(f"✅ Read {local_file} ({len(content):,} bytes)")
    
    # Create deployment script
    deploy_script = "#!/bin/bash\nset -e\n"
    deploy_script += f"cd /home/{VM_USER}\n\n"
    
    for remote_path, file_info in files_content.items():
        filename = os.path.basename(remote_path)
        content_b64 = base64.b64encode(file_info['content'].encode('utf-8')).decode('utf-8')
        deploy_script += f"# Deploy {filename}\n"
        deploy_script += f"echo '{content_b64}' | base64 -d > {remote_path}\n"
        deploy_script += f"chmod 644 {remote_path}\n\n"
    
    # Make main script executable
    deploy_script += f"chmod +x /home/{VM_USER}/vm_inventory_updater.py\n"
    deploy_script += "echo '✅ Files deployed'\n"
    
    # Update VM metadata
    try:
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        metadata = instance.get('metadata', {})
        fingerprint = metadata.get('fingerprint', '')
        items = metadata.get('items', [])
        
        # Remove old deploy scripts
        items = [item for item in items if item.get('key') not in ['deploy-script', 'deploy-files']]
        
        # Add deployment script
        items.append({
            'key': 'deploy-files',
            'value': deploy_script
        })
        
        compute.instances().setMetadata(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME,
            body={
                'fingerprint': fingerprint,
                'items': items
            }
        ).execute()
        
        print("\n✅ Deployment script added to VM metadata")
        print("\nTo execute deployment, SSH to VM and run:")
        print(f"   curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-files | bash")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error deploying files: {e}")
        return False

def setup_cron(compute):
    """Set up cron job on VM"""
    print("\n" + "="*80)
    print("SETTING UP CRON JOB")
    print("="*80)
    
    cron_script = f"""#!/bin/bash
# Set up cron job for inventory updater
cd /home/{VM_USER}

# Create cron job (runs every 5 minutes)
(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/{VM_USER} && /usr/bin/python3 /home/{VM_USER}/vm_inventory_updater.py >> /home/{VM_USER}/inventory_cron.log 2>&1") | crontab -

echo "✅ Cron job configured"
crontab -l
"""
    
    try:
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        metadata = instance.get('metadata', {})
        fingerprint = metadata.get('fingerprint', '')
        items = metadata.get('items', [])
        
        items = [item for item in items if item.get('key') != 'setup-cron']
        items.append({
            'key': 'setup-cron',
            'value': cron_script
        })
        
        compute.instances().setMetadata(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME,
            body={
                'fingerprint': fingerprint,
                'items': items
        }).execute()
        
        print("✅ Cron setup script added to metadata")
        print("\nTo set up cron, SSH to VM and run:")
        print(f"   curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/setup-cron | bash")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error setting up cron: {e}")
        return False

def main():
    print("="*80)
    print("CREATE NEW VM AND DEPLOY INVENTORY UPDATER")
    print("="*80)
    
    # Authenticate
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
        
        print("\n✅ Authenticated")
    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        return False
    
    # Create VM
    if not create_vm(compute):
        return False
    
    # Deploy files
    if not deploy_files(compute):
        return False
    
    # Setup cron
    if not setup_cron(compute):
        return False
    
    print("\n" + "="*80)
    print("✅ VM CREATED AND READY FOR DEPLOYMENT")
    print("="*80)
    print(f"\nVM Name: {VM_NAME}")
    print(f"Zone: {ZONE}")
    print("\nNext steps:")
    print("1. SSH to VM:")
    print(f"   gcloud compute ssh {VM_NAME} --zone={ZONE} --project={PROJECT_ID}")
    print("\n2. Deploy files:")
    print("   curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-files | bash")
    print("\n3. Set up cron:")
    print("   curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/setup-cron | bash")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
