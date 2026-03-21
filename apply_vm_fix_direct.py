#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply VM fix directly using gcloud commands
No temp directories needed - uses inline commands
"""

import subprocess
import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

VM_NAME = "inventory-updater-vm"
VM_ZONE = "us-central1-a"
SCRIPT_PATH = "/home/banzo/vm_inventory_updater.py"

# Find gcloud path
GCLOUD_PATH = r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
if not os.path.exists(GCLOUD_PATH):
    GCLOUD_PATH = 'gcloud'

def run_vm_command(command):
    """Run a command on the VM"""
    try:
        result = subprocess.run(
            [GCLOUD_PATH, 'compute', 'ssh', VM_NAME,
             '--zone', VM_ZONE,
             '--command', command],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def check_vm_code():
    """Check the current code on VM"""
    print("="*80)
    print("CHECKING VM CODE")
    print("="*80)
    print()
    
    # Check if file exists
    success, output, error = run_vm_command(f"test -f {SCRIPT_PATH} && echo 'EXISTS' || echo 'NOT_FOUND'")
    
    if not success or 'NOT_FOUND' in output:
        print(f"❌ Script not found at {SCRIPT_PATH}")
        return False
    
    print(f"✅ Script exists at {SCRIPT_PATH}")
    
    # Check if fix already applied
    success, output, error = run_vm_command(f"grep -q 'FIX FOR PROMOTION ITEMS' {SCRIPT_PATH} && echo 'FIXED' || echo 'NOT_FIXED'")
    
    if success and 'FIXED' in output:
        print("⚠️  Fix already applied!")
        return True
    
    print("Fix not yet applied")
    
    # Get the relevant code section
    print("\nCurrent code around quantity handling:")
    print("-" * 80)
    success, output, error = run_vm_command(f"grep -n 'quantity = 1' {SCRIPT_PATH} | head -5")
    if success:
        print(output)
    
    success, output, error = run_vm_command(f"sed -n '870,880p' {SCRIPT_PATH}")
    if success:
        for i, line in enumerate(output.split('\n'), start=870):
            if line.strip():
                print(f"{i:4d}: {line}")
    print("-" * 80)
    
    return True

def apply_fix():
    """Apply the fix directly on VM"""
    print()
    print("="*80)
    print("APPLYING FIX ON VM")
    print("="*80)
    print()
    
    # Create Python script inline
    fix_script = """python3 << 'ENDOFSCRIPT'
import re
import shutil
from datetime import datetime

script_file = "/home/banzo/vm_inventory_updater.py"
backup_file = f"{script_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

print("Reading script file...")
with open(script_file, 'r', encoding='utf-8') as f:
    content = f.read()

if "FIX FOR PROMOTION ITEMS" in content:
    print("Fix already applied!")
    exit(0)

shutil.copy(script_file, backup_file)
print(f"Backup created: {backup_file}")

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
    print("Fix applied successfully!")
    
    # Verify
    print("Verification:")
    with open(script_file, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if "FIX FOR PROMOTION ITEMS" in line:
                for j in range(i, min(i+12, len(lines))):
                    print(f"{j+1:4d}: {lines[j].rstrip()}")
                break
else:
    print("Could not find pattern to replace")
    exit(1)
ENDOFSCRIPT"""
    
    success, output, error = run_vm_command(fix_script)
    
    print(output)
    if error:
        print("STDERR:", error)
    
    if success:
        print("\n✅ Fix applied successfully!")
        return True
    else:
        print("\n❌ Error applying fix")
        return False

def verify_fix():
    """Verify the fix was applied"""
    print()
    print("="*80)
    print("VERIFYING FIX")
    print("="*80)
    print()
    
    success, output, error = run_vm_command(f"grep -A 10 'FIX FOR PROMOTION ITEMS' {SCRIPT_PATH}")
    
    if success and output.strip():
        print("✅ Fix found in code:")
        print("-" * 80)
        print(output)
        print("-" * 80)
        return True
    else:
        print("❌ Fix not found")
        return False

if __name__ == "__main__":
    print()
    
    # Step 1: Check current code
    if not check_vm_code():
        print("\n❌ Cannot proceed - script not found on VM")
        sys.exit(1)
    
    # Step 2: Apply fix
    if apply_fix():
        # Step 3: Verify
        if verify_fix():
            print("\n" + "="*80)
            print("✅ ALL DONE!")
            print("="*80)
            print("\nThe VM code has been fixed.")
            print("Future inventory updates will correctly count promotion items.")
        else:
            print("\n⚠️  Fix applied but verification failed")
    else:
        print("\n❌ Failed to apply fix")
        sys.exit(1)
