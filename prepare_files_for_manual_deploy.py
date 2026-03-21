#!/usr/bin/env python3
"""
Prepare file contents for manual copy-paste deployment
This creates files with the exact content to paste into the VM
"""

import os
import base64

FILES_TO_DEPLOY = {
    "vm_inventory_updater_fixed.py": "/home/banzo/vm_inventory_updater.py",
    "clover_creds.json": "/home/banzo/clover_creds.json",
    "service-account-key.json": "/home/banzo/service-account-key.json"
}

print("="*80)
print("PREPARING FILES FOR MANUAL DEPLOYMENT")
print("="*80)
print("\nThis will create files you can copy-paste into the VM via SSH\n")

output_dir = "files_for_manual_deploy"
os.makedirs(output_dir, exist_ok=True)

for local_file, remote_path in FILES_TO_DEPLOY.items():
    if not os.path.exists(local_file):
        print(f"ERROR: {local_file} not found!")
        continue
    
    filename = os.path.basename(remote_path)
    output_file = os.path.join(output_dir, filename)
    
    with open(local_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Save file content
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    file_size = len(content)
    print(f"OK: Prepared {filename}")
    print(f"   Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    print(f"   Location: {output_file}")
    
    # Show first few lines
    lines = content.split('\n')[:5]
    print(f"   Preview: {lines[0][:60]}...")
    print()

print("="*80)
print("FILES READY FOR MANUAL DEPLOYMENT")
print("="*80)
print(f"\nFiles saved to: {output_dir}/")
print("\nNext steps:")
print("1. SSH into VM via Google Cloud Console")
print("2. For each file, run:")
print("   nano /home/banzo/[filename]")
print("3. Copy content from the prepared files")
print("4. Paste into nano, save (Ctrl+X, Y, Enter)")
print("\nOr use the file upload feature in the SSH terminal if available!")
