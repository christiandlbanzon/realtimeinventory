#!/usr/bin/env python3
import re
import shutil
from datetime import datetime

script_file = "/home/banzo/vm_inventory_updater.py"
backup_file = f"{script_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

print("="*80)
print("APPLYING PROMOTION QUANTITY FIX")
print("="*80)
print()

print(f"Script file: {script_file}")
print(f"Backup file: {backup_file}")
print()

print("Reading script file...")
with open(script_file, 'r', encoding='utf-8') as f:
    content = f.read()

if "FIX FOR PROMOTION ITEMS" in content:
    print("⚠️  Fix already applied!")
    exit(0)

shutil.copy(script_file, backup_file)
print(f"✅ Backup created: {backup_file}")

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
    
    print("\nVerification:")
    with open(script_file, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if "FIX FOR PROMOTION ITEMS" in line:
                for j in range(i, min(i+12, len(lines))):
                    print(f"{j+1:4d}: {lines[j].rstrip()}")
                break
else:
    print("❌ Could not find pattern to replace")
    exit(1)

print("\n✅ Fix complete!")
