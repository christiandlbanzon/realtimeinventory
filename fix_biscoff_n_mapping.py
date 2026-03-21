#!/usr/bin/env python3
"""
Fix the mapping for *N* Cheesecake with Biscoff to properly identify it as N - Cheesecake with Biscoff
This script extracts the Python code from deploy_temp.sh, fixes it, and creates a proper vm_inventory_updater.py
"""

import re
import os
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def extract_python_from_sh(sh_file):
    """Extract Python code from deploy_temp.sh"""
    print("="*80)
    print("EXTRACTING PYTHON CODE FROM deploy_temp.sh")
    print("="*80)
    
    with open(sh_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find Python code block (between python3 << 'PYTHON_SCRIPT' and PYTHON_SCRIPT)
    pattern = r"python3\s+<<\s+'PYTHON_SCRIPT'\s*\n(.*?)\nPYTHON_SCRIPT"
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        python_code = match.group(1)
        return python_code
    else:
        # Try alternative pattern - maybe it's just Python code
        if 'def clean_cookie_name' in content:
            # It might be a Python file with .sh extension
            return content
        return None

def fix_biscoff_mapping(python_code):
    """Fix the Biscoff mapping in the Python code"""
    print("\n" + "="*80)
    print("FIXING BISCOFF MAPPING")
    print("="*80)
    
    # Count occurrences before fix
    n_mappings_before = python_code.count('"*N* Cheesecake with Biscoff"')
    h_mappings_before = python_code.count('"*H* Cheesecake with Biscoff"')
    
    print(f"\nBefore fix:")
    print(f"  *N* mappings: {n_mappings_before}")
    print(f"  *H* mappings: {h_mappings_before}")
    
    # Fix 1: Add *N* to montehiedra_mapping
    if '"*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff"' not in python_code:
        # Find montehiedra_mapping and add *N* entry
        pattern = r'(\s+"\*H\* Cheesecake with Biscoff": "H - Cheesecake with Biscoff",\s*\n)'
        replacement = r'\1        "*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff",\n        "*N* Cheesecake with Biscoff ": "N - Cheesecake with Biscoff",\n'
        python_code = re.sub(pattern, replacement, python_code)
        print("  ✅ Added *N* to montehiedra_mapping")
    
    # Fix 2: Add *N* to name_mapping (first occurrence)
    if '"*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff"' not in python_code.split('name_mapping = {')[1].split('}')[0] if 'name_mapping = {' in python_code else '':
        pattern = r'(\s+"\*H\* Cheesecake with Biscoff": "H - Cheesecake with Biscoff",\s*\n\s+"\*I\* Tres Leches")'
        replacement = r'\1\n        "*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff",'
        python_code = re.sub(pattern, replacement, python_code)
        print("  ✅ Added *N* to name_mapping (first section)")
    
    # Fix 3: Add *N* to name_mapping (trailing spaces section)
    pattern = r'(\s+"\*H\* Cheesecake with Biscoff": "H - Cheesecake with Biscoff",\s*\n\s+"\*I\* Tres Leches")'
    if re.search(pattern, python_code):
        replacement = r'\1\n        "*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff",\n        "*N* Cheesecake with Biscoff ": "N - Cheesecake with Biscoff",'
        python_code = re.sub(pattern, replacement, python_code)
        print("  ✅ Added *N* to name_mapping (trailing spaces section)")
    
    # Fix 4: Change fallback mapping from H to N
    pattern = r'"Cheesecake with Biscoff": "H - Cheesecake with Biscoff"'
    if pattern in python_code:
        python_code = python_code.replace(pattern, '"Cheesecake with Biscoff": "N - Cheesecake with Biscoff"  # Fixed: Changed from H to N')
        print("  ✅ Changed fallback mapping from H to N")
    
    # Fix 5: Add *N* with registered symbol
    if '"*N* Cheesecake with Biscoff®": "N - Cheesecake with Biscoff"' not in python_code:
        # Find the special characters section and add it
        pattern = r'("Cheesecake with Biscoff┬«": "[^"]+",\s*\n)'
        replacement = r'\1        "*N* Cheesecake with Biscoff®": "N - Cheesecake with Biscoff",  # Handle registered symbol\n        "*N* Cheesecake with Biscoff ": "N - Cheesecake with Biscoff",  # Handle trailing space\n'
        python_code = re.sub(pattern, replacement, python_code)
        print("  ✅ Added *N* with registered symbol mapping")
    
    # Count occurrences after fix
    n_mappings_after = python_code.count('"*N* Cheesecake with Biscoff"')
    
    print(f"\nAfter fix:")
    print(f"  *N* mappings: {n_mappings_after}")
    print(f"  *H* mappings: {h_mappings_before} (kept for other locations)")
    
    return python_code

def main():
    """Main function"""
    print("="*80)
    print("FIX BISCOFF N MAPPING")
    print("="*80)
    
    sh_file = "deploy_temp.sh"
    if not os.path.exists(sh_file):
        print(f"ERROR: {sh_file} not found!")
        return False
    
    # Extract Python code
    python_code = extract_python_from_sh(sh_file)
    if not python_code:
        print("ERROR: Could not extract Python code from deploy_temp.sh")
        print("The file might not contain Python code in the expected format")
        return False
    
    # Fix the mapping
    fixed_code = fix_biscoff_mapping(python_code)
    
    # Write to vm_inventory_updater.py
    output_file = "vm_inventory_updater_fixed.py"
    print(f"\n{'='*80}")
    print(f"WRITING FIXED CODE TO {output_file}")
    print(f"{'='*80}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(fixed_code)
    
    print(f"\n✅ Fixed code written to {output_file}")
    print(f"\nNext steps:")
    print(f"  1. Review {output_file} to ensure the fixes are correct")
    print(f"  2. Deploy it to the VM as vm_inventory_updater.py")
    print(f"  3. Test that *N* Cheesecake with Biscoff is properly identified")
    
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
