#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply the promotion quantity fix to VM code
Uses gcloud to copy and apply the fix
"""

import subprocess
import os
import sys
import tempfile
import shutil

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

VM_NAME = "inventory-updater-vm"
VM_ZONE = "us-central1-a"
VM_SCRIPT = "/home/banzo/vm_inventory_updater.py"

# Find gcloud path
GCLOUD_PATH = r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
if not os.path.exists(GCLOUD_PATH):
    GCLOUD_PATH = 'gcloud'

def get_env():
    env = os.environ.copy()
    temp_config = tempfile.mkdtemp()
    env['CLOUDSDK_CONFIG'] = temp_config
    env['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath('service-account-key.json')
    for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
        env.pop(proxy_var, None)
    return env, temp_config

def create_fix_script():
    """Create a script to apply the fix on the VM"""
    fix_script = '''#!/bin/bash
# Fix for promotion items quantity handling

SCRIPT_FILE="/home/banzo/vm_inventory_updater.py"
BACKUP_FILE="${SCRIPT_FILE}.backup.$(date +%Y%m%d_%H%M%S)"

echo "Applying promotion quantity fix..."
echo "Backup: $BACKUP_FILE"

# Create backup
cp "$SCRIPT_FILE" "$BACKUP_FILE"
echo "✅ Backup created: $BACKUP_FILE"

# Check if fix already applied
if grep -q "FIX FOR PROMOTION ITEMS" "$SCRIPT_FILE"; then
    echo "⚠️  Fix already applied!"
    exit 0
fi

# Apply fix using sed
# Find the line with "quantity = 1" and replace the section
sed -i '/# SAFEGUARD: Each line item represents 1 unit sold/,/quantity = 1/c\
                    # SAFEGUARD: Each line item represents 1 unit sold (Clover API doesn'\''t have quantity field)\
                    # FIX FOR PROMOTION ITEMS: Items in promotions have quantity=0 but still count as 1 unit\
                    # Check if quantity exists and is valid, otherwise default to 1\
                    api_quantity = item.get('\''quantity'\'', 0)\
                    if api_quantity == 0:\
                        # Promotion items have quantity=0 but each line item = 1 unit sold\
                        quantity = 1\
                    else:\
                        # Normal items: convert from millis to units (1000 millis = 1 unit)\
                        quantity = int(api_quantity / 1000) if api_quantity > 0 else 1\
                    \
                    # Ensure minimum of 1 unit per line item (safety check)\
                    quantity = max(quantity, 1)' "$SCRIPT_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Fix applied successfully!"
    echo ""
    echo "Verification:"
    grep -A 10 "FIX FOR PROMOTION ITEMS" "$SCRIPT_FILE" | head -12
else
    echo "❌ Error applying fix - restoring backup"
    cp "$BACKUP_FILE" "$SCRIPT_FILE"
    exit 1
fi
'''
    return fix_script

def apply_fix_via_python():
    """Apply fix using Python script on VM"""
    print("="*80)
    print("APPLYING VM CODE FIX")
    print("="*80)
    print()
    
    env, temp_config = get_env()
    
    try:
        # Create Python fix script
        fix_script_content = """#!/usr/bin/env python3
import re
import sys
import shutil
from datetime import datetime

script_file = "/home/banzo/vm_inventory_updater.py"
backup_file = f"{script_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

print("Reading script file...")
with open(script_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Check if already fixed
if "FIX FOR PROMOTION ITEMS" in content:
    print("⚠️  Fix already applied!")
    sys.exit(0)

# Create backup
shutil.copy(script_file, backup_file)
print(f"✅ Backup created: {backup_file}")

# Find and replace the quantity assignment
pattern = r'(# SAFEGUARD: Each line item represents 1 unit sold.*?quantity = 1)'
replacement = '''# SAFEGUARD: Each line item represents 1 unit sold (Clover API doesn't have quantity field)
                    # FIX FOR PROMOTION ITEMS: Items in promotions have quantity=0 but still count as 1 unit
                    # Check if quantity exists and is valid, otherwise default to 1
                    api_quantity = item.get('quantity', 0)
                    if api_quantity == 0:
                        # Promotion items have quantity=0 but each line item = 1 unit sold
                        quantity = 1
                    else:
                        # Normal items: convert from millis to units (1000 millis = 1 unit)
                        quantity = int(api_quantity / 1000) if api_quantity > 0 else 1
                    
                    # Ensure minimum of 1 unit per line item (safety check)
                    quantity = max(quantity, 1)'''

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

if new_content != content:
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("✅ Fix applied successfully!")
    
    # Verify
    print("\\nVerification:")
    with open(script_file, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if "FIX FOR PROMOTION ITEMS" in line:
                for j in range(i, min(i+12, len(lines))):
                    print(f"{j+1:4d}: {lines[j].rstrip()}")
                break
else:
    print("❌ Could not find pattern to replace")
    sys.exit(1)
"""
        
        # Write fix script to temp file
        fix_file = 'apply_fix_on_vm.py'
        with open(fix_file, 'w', encoding='utf-8') as f:
            f.write(fix_script_content)
        
        print(f"Created fix script: {fix_file}")
        
        print("[1] Copying fix script to VM...")
        result = subprocess.run(
            [GCLOUD_PATH, 'compute', 'scp', fix_file,
             f'{VM_NAME}:{fix_file}',
             '--zone', VM_ZONE],
            env=env,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"❌ Error copying script: {result.stderr}")
            return False
        
        print("✅ Script copied")
        
        print("\n[2] Running fix script on VM...")
        result = subprocess.run(
            [GCLOUD_PATH, 'compute', 'ssh', VM_NAME,
             '--zone', VM_ZONE,
             '--command', f'python3 {fix_file}'],
            env=env,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print("\n✅ Fix applied successfully on VM!")
            return True
        else:
            print(f"\n❌ Error applying fix: {result.returncode}")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        try:
            if os.path.exists(fix_file):
                os.remove(fix_file)
            shutil.rmtree(temp_config, ignore_errors=True)
        except:
            pass

if __name__ == "__main__":
    success = apply_fix_via_python()
    sys.exit(0 if success else 1)
