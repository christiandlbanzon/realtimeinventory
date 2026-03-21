#!/usr/bin/env python3
"""
Clean up codebase and deploy only essential files to VM
"""

import os
import sys
import shutil
import glob

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Essential files to KEEP
ESSENTIAL_FILES = {
    'vm_inventory_updater_fixed.py',
    'clover_creds.json',
    'service-account-key.json',
    'deploy.ps1',
    'create_and_deploy_new_vm.py',
    'deploy_to_any_vm.py',
    'NEW_VM_SUMMARY.md',
    'DEPLOY_NEW_VM.md',
}

# Directories to KEEP
KEEP_DIRS = {'.venv', '.git', 'scripts', '.gcloud_temp_config'}

def cleanup_codebase():
    """Remove all unnecessary files"""
    print("="*80)
    print("CLEANING UP CODEBASE")
    print("="*80)
    
    base_dir = os.getcwd()
    deleted = []
    errors = []
    
    # Get all files
    for root, dirs, files in os.walk(base_dir):
        # Skip keep directories
        dirs[:] = [d for d in dirs if d not in KEEP_DIRS and not d.startswith('.')]
        
        for filename in files:
            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, base_dir)
            
            # Skip essential files
            if filename in ESSENTIAL_FILES:
                continue
            
            # Skip if in keep directory
            if any(keep_dir in rel_path for keep_dir in KEEP_DIRS):
                continue
            
            # Delete everything else
            try:
                os.remove(filepath)
                deleted.append(rel_path)
                print(f"🗑️  Deleted: {rel_path}")
            except PermissionError:
                errors.append(rel_path)
            except Exception as e:
                errors.append(f"{rel_path}: {e}")
    
    # Clean up empty directories
    for root, dirs, files in os.walk(base_dir, topdown=False):
        if root == base_dir:
            continue
        
        dirname = os.path.basename(root)
        if dirname in KEEP_DIRS or dirname.startswith('.'):
            continue
        
        try:
            if not os.listdir(root):
                os.rmdir(root)
                print(f"🗑️  Deleted empty dir: {os.path.relpath(root, base_dir)}")
        except:
            pass
    
    print(f"\n✅ Deleted {len(deleted)} files")
    if errors:
        print(f"⚠️  {len(errors)} files couldn't be deleted (may be open)")
    
    return len(deleted)

def deploy_essentials_to_vm():
    """Deploy only essential files to VM"""
    print("\n" + "="*80)
    print("DEPLOYING ESSENTIAL FILES TO VM")
    print("="*80)
    
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2
    import base64
    
    PROJECT_ID = "boxwood-chassis-332307"
    ZONE = "us-central1-a"
    VM_NAME = "real-time-inventory"  # Updated to new name
    VM_USER = "banzo"
    
    # Files to deploy
    files_to_deploy = {
        'vm_inventory_updater_fixed.py': '/home/banzo/vm_inventory_updater.py',
        'clover_creds.json': '/home/banzo/clover_creds.json',
        'service-account-key.json': '/home/banzo/service-account-key.json',
    }
    
    # Read files
    files_content = {}
    for local_file, remote_path in files_to_deploy.items():
        if not os.path.exists(local_file):
            print(f"❌ File not found: {local_file}")
            return False
        
        with open(local_file, 'r', encoding='utf-8') as f:
            content = f.read()
            files_content[remote_path] = {
                'content': content,
                'size': len(content)
            }
            print(f"✅ Read {local_file} ({len(content):,} bytes)")
    
    # Create clean deployment script
    deploy_script = f"""#!/bin/bash
set -e
cd /home/{VM_USER}

echo "🧹 Cleaning up old files..."
rm -f /home/{VM_USER}/*.py.backup*
rm -f /home/{VM_USER}/*.log
rm -f /home/{VM_USER}/deployment.log

echo "📦 Deploying essential files..."
"""
    
    for remote_path, file_info in files_content.items():
        filename = os.path.basename(remote_path)
        content_b64 = base64.b64encode(file_info['content'].encode('utf-8')).decode('utf-8')
        deploy_script += f"""
# Deploy {filename}
echo '{content_b64}' | base64 -d > {remote_path}
chmod 644 {remote_path}
echo "  ✅ {filename}"
"""
    
    deploy_script += f"""
# Make main script executable
chmod +x /home/{VM_USER}/vm_inventory_updater.py

# Set up cron (clean)
(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/{VM_USER} && /usr/bin/python3 /home/{VM_USER}/vm_inventory_updater.py >> /home/{VM_USER}/inventory_cron.log 2>&1") | crontab -

echo ""
echo "✅ Deployment complete!"
echo "📁 Files on VM:"
ls -lh /home/{VM_USER}/*.py /home/{VM_USER}/*.json 2>/dev/null | grep -v ".backup"
echo ""
echo "⏰ Cron jobs:"
crontab -l
"""
    
    # Authenticate and deploy
    try:
        credentials = service_account.Credentials.from_service_account_file(
            'service-account-key.json',
            scopes=[
                'https://www.googleapis.com/auth/cloud-platform',
                'https://www.googleapis.com/auth/compute'
            ]
        )
        
        http = httplib2.Http(proxy_info=None)
        authorized_http = AuthorizedHttp(credentials, http=http)
        compute = build('compute', 'v1', http=authorized_http)
        
        instance = compute.instances().get(
            project=PROJECT_ID,
            zone=ZONE,
            instance=VM_NAME
        ).execute()
        
        metadata = instance.get('metadata', {})
        fingerprint = metadata.get('fingerprint', '')
        items = metadata.get('items', [])
        
        # Remove old scripts, keep only clean deploy
        items = [item for item in items if item.get('key') not in ['deploy-files', 'deploy-script', 'setup-cron', 'startup-script']]
        
        items.append({
            'key': 'deploy-clean',
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
        
        print("\n✅ Clean deployment script added to VM")
        print("\n📋 To deploy, SSH to VM and run:")
        print(f"   gcloud compute ssh {VM_NAME} --zone={ZONE} --project={PROJECT_ID}")
        print("   curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-clean | bash")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error deploying: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*80)
    print("CLEANUP CODEBASE AND DEPLOY TO VM")
    print("="*80)
    
    # Cleanup
    deleted_count = cleanup_codebase()
    
    # Deploy
    deploy_success = deploy_essentials_to_vm()
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"✅ Cleaned up: {deleted_count} files")
    print(f"{'✅' if deploy_success else '❌'} Deployment script ready")
    print("\n📁 Essential files kept:")
    for f in sorted(ESSENTIAL_FILES):
        if os.path.exists(f):
            print(f"   ✅ {f}")
    
    print("\n🚀 Next step: SSH to VM and run the deploy-clean script")

if __name__ == "__main__":
    main()
