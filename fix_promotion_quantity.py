#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix for promotion items: When quantity is 0, count as 1 unit
This script shows the fix needed in vm_inventory_updater.py
"""

print("="*80)
print("FIX FOR PROMOTION ITEMS - QUANTITY COUNTING")
print("="*80)
print()

print("PROBLEM:")
print("  - Promotion items in Clover have quantity=0")
print("  - But they still represent 1 unit sold")
print("  - Current code: cookie_sales[item_name] += quantity  (adds 0)")
print("  - Result: Sheet shows 0 instead of actual count")
print()

print("SOLUTION:")
print("  When quantity is 0 or missing, count as 1 unit")
print()

print("CODE CHANGE NEEDED:")
print("-" * 80)
print("""
# OLD CODE (line ~959 in deploy_temp.sh):
quantity = item.get('quantity', 0)
if quantity == 0:
    quantity = 0  # This causes the problem!

# NEW CODE:
quantity = item.get('quantity', 0)
if quantity == 0:
    quantity = 1000  # Count as 1 unit (Clover uses millis, so 1000 = 1)

# OR BETTER:
quantity = item.get('quantity', 0)
# If quantity is 0, it's likely a promotion item - count as 1
if quantity == 0:
    quantity = 1000  # 1 unit in Clover's millis format
else:
    # Quantity is already in millis, use as-is
    pass

# Then when counting:
qty_decimal = quantity / 1000  # Convert millis to decimal
cookie_sales[item_name] += int(qty_decimal)  # Add to count
""")

print()
print("="*80)
print("LOCATION IN CODE:")
print("="*80)
print("File: vm_inventory_updater.py (or deploy_temp.sh)")
print("Function: fetch_clover_sales()")
print("Approximate line: ~950-960")
print()
print("The fix should be applied where quantity is extracted from line items")
print("and before it's added to cookie_sales dictionary")
