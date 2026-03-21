#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply the promotion quantity fix to vm_inventory_updater.py
This script can be run on the VM to apply the fix
"""

import sys
import re

def apply_fix(file_path):
    """Apply the promotion quantity fix to the file"""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Find the section where quantity = 1 is set
        # Look for the comment about "Each line item represents 1 unit sold"
        pattern = r'(# SAFEGUARD: Each line item represents 1 unit sold.*?\n.*?# DO NOT try to read a \'quantity\' field.*?\n.*?quantity = 1)'
        
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
        
        # Try to replace
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        if new_content == original_content:
            # Try alternative pattern
            pattern2 = r'(quantity = 1\s+#.*?Each line item)'
            replacement2 = '''api_quantity = item.get('quantity', 0)
                    if api_quantity == 0:
                        quantity = 1  # Promotion items: count as 1 unit
                    else:
                        quantity = int(api_quantity / 1000) if api_quantity > 0 else 1
                    quantity = max(quantity, 1)  # Ensure minimum of 1 unit per line item'''
            
            new_content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)
        
        if new_content != original_content:
            # Backup original
            backup_path = file_path + '.backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            print(f"✅ Created backup: {backup_path}")
            
            # Write fixed content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ Applied fix to: {file_path}")
            return True
        else:
            print("⚠️  Could not find exact pattern to replace")
            print("   The file might already be fixed or have different structure")
            return False
            
    except Exception as e:
        print(f"❌ Error applying fix: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "vm_inventory_updater.py"
    
    print("="*80)
    print("APPLYING PROMOTION QUANTITY FIX")
    print("="*80)
    print(f"File: {file_path}")
    print()
    
    success = apply_fix(file_path)
    
    if success:
        print("\n✅ Fix applied successfully!")
        print("   The script will now correctly count promotion items (quantity=0) as 1 unit")
    else:
        print("\n⚠️  Fix not applied - manual review needed")
