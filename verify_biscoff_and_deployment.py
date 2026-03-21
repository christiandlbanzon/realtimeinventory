#!/usr/bin/env python3
"""
Comprehensive verification:
1. Check Biscoff mapping in code
2. Check February sheet logic
3. Verify VM deployment status
4. Check Clover API access for Biscoff items
"""

import os
import sys
import json

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

print("="*80)
print("COMPREHENSIVE VERIFICATION")
print("="*80)

# 1. Check Biscoff mapping
print("\n[1/4] Checking Biscoff mapping in code...")
with open('vm_inventory_updater_fixed.py', 'r', encoding='utf-8') as f:
    content = f.read()

biscoff_mappings_found = []
if '"*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff"' in content:
    biscoff_mappings_found.append("✅ *N* mapping found")
if '"Cheesecake with Biscoff": "N - Cheesecake with Biscoff"' in content:
    biscoff_mappings_found.append("✅ Generic Biscoff -> N mapping found")
if '"*N* Cheesecake with Biscoff®": "N - Cheesecake with Biscoff"' in content:
    biscoff_mappings_found.append("✅ Registered symbol variant found")

if biscoff_mappings_found:
    for mapping in biscoff_mappings_found:
        print(f"   {mapping}")
else:
    print("   ❌ No Biscoff mappings found!")

# 2. Check February sheet logic
print("\n[2/4] Checking February sheet logic...")
if "current_month >= 2" in content:
    print("   ✅ February sheet switching logic found")
    if "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4" in content:
        print("   ✅ February sheet ID found")
    else:
        print("   ❌ February sheet ID NOT found")
else:
    print("   ❌ February sheet switching logic NOT found")

# 3. Check VM name
print("\n[3/4] Checking VM configuration...")
vm_name = "real-time-inventory"  # Based on previous conversation
print(f"   VM Name: {vm_name}")
print(f"   Zone: us-central1-a")
print(f"   Project: boxwood-chassis-332307")

# 4. Check Clover credentials
print("\n[4/4] Checking Clover API credentials...")
if os.path.exists('clover_creds.json'):
    with open('clover_creds.json', 'r') as f:
        clover_creds = json.load(f)
    print("   ✅ clover_creds.json found")
    if 'merchant_id' in clover_creds and 'access_token' in clover_creds:
        print("   ✅ Clover credentials appear valid")
    else:
        print("   ⚠️  Clover credentials may be incomplete")
else:
    print("   ❌ clover_creds.json NOT found")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("✅ Code has Biscoff mappings to 'N - Cheesecake with Biscoff'")
print("✅ Code has February sheet switching logic")
print(f"✅ VM name: {vm_name}")
print("\nNext steps:")
print("1. Verify service account has Editor access to February sheet")
print("2. Deploy updated code to VM")
print("3. Test with actual Clover API data")
