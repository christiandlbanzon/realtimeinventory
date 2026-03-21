#!/usr/bin/env python3
"""
Check Biscoff mapping in the code to ensure it's correct
"""

import re

# Read the file
with open('vm_inventory_updater_fixed.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all Biscoff-related mappings
print("="*80)
print("CHECKING BISCOFF MAPPINGS")
print("="*80)

# Find clean_cookie_name function
match = re.search(r'def clean_cookie_name\(api_name\):.*?(?=\ndef |\Z)', content, re.DOTALL)
if match:
    func_content = match.group(0)
    
    # Find all mappings that contain Biscoff
    biscoff_mappings = []
    for line in func_content.split('\n'):
        if 'biscoff' in line.lower() or 'Biscoff' in line:
            biscoff_mappings.append(line.strip())
    
    print("\nFound Biscoff mappings:")
    for i, mapping in enumerate(biscoff_mappings, 1):
        print(f"{i}. {mapping}")
    
    # Check if N mapping exists
    has_n_mapping = any('"N - Cheesecake with Biscoff"' in m or "'N - Cheesecake with Biscoff'" in m for m in biscoff_mappings)
    print(f"\n✅ Has N mapping: {has_n_mapping}")
    
    # Check for common Clover API variations
    variations_to_check = [
        "*N* Cheesecake with Biscoff",
        "*N* Cheesecake with Biscoff ",
        "*N* Cheesecake with Biscoff®",
        "N - Cheesecake with Biscoff",
        "Cheesecake with Biscoff"
    ]
    
    print("\nChecking for common variations:")
    for var in variations_to_check:
        if var in func_content:
            print(f"  ✅ Found: {var}")
        else:
            print(f"  ❌ Missing: {var}")

# Check February sheet logic
print("\n" + "="*80)
print("CHECKING FEBRUARY SHEET LOGIC")
print("="*80)

if "current_month >= 2" in content:
    print("✅ February sheet switching logic found")
    if "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4" in content:
        print("✅ February sheet ID found in code")
    else:
        print("❌ February sheet ID NOT found")
else:
    print("❌ February sheet switching logic NOT found")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("The code should map Clover API names containing 'Biscoff' to 'N - Cheesecake with Biscoff'")
print("And switch to February sheet when month >= 2")
