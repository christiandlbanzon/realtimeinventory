# Cheesecake with Biscoff Debug - Complete Analysis

## Problem Summary

**Issue**: Cheesecake with Biscoff shows **0** in Google Sheet on January 28, but Clover dashboard shows **14 sold**.

**Location**: Old San Juan (VSJ), Row 16, Column BU (Live Sales Data)

---

## Root Cause Identified ✅

### The Issue: Promotion Items Have Quantity = 0

When items are part of a promotion/bundle in Clover:
- The Clover API returns line items with `quantity: 0`
- But each line item still represents **1 unit sold**
- The dashboard correctly counts these as 1 unit each
- The current code adds `quantity` (which is 0) to the count, resulting in 0

### Evidence

1. **Clover Dashboard**: Shows 14 units sold ✅
2. **Clover API**: Returns 14 line items, all with `quantity: 0` ❌
3. **Google Sheet**: Shows 0 ❌
4. **Debug Test**: Counting each line item as 1 unit = 14 ✅ (matches dashboard)

---

## Code Fix Required

### Location
File: `vm_inventory_updater.py`  
Function: `fetch_clover_sales()`  
Approximate line: ~874-960

### Current Code (Problematic)
```python
# Line ~874: Sets quantity = 1 (correct)
quantity = 1  # Each line item = 1 unit

# But then later when processing:
for item in line_items:
    quantity = item.get('quantity', 0)  # This gets 0 for promotion items!
    cookie_sales[item_name] += quantity  # Adds 0 instead of 1
```

### Fixed Code
```python
# When processing line items:
for item in line_items:
    quantity = item.get('quantity', 0)
    
    # FIX: If quantity is 0 (promotion item), count as 1 unit
    # Each line item represents 1 unit sold, regardless of quantity field
    if quantity == 0:
        quantity = 1000  # 1 unit in Clover's millis format (1000 = 1.0)
    
    # Convert millis to decimal
    qty_decimal = quantity / 1000
    
    # Add to count
    cookie_sales[item_name] += int(qty_decimal)
```

**OR simpler approach** (if code already sets `quantity = 1`):
```python
# Just ensure quantity is always 1 per line item
quantity = 1  # Each line item = 1 unit (don't read from API for promotions)
cookie_sales[item_name] += quantity
```

---

## Additional Verification

### Cookie Name Mapping ✅
- API Name: `*N* Cheesecake with Biscoff®`
- Maps to: `N - Cheesecake with Biscoff` ✅
- Sheet Row: 16 ✅

### Location Mapping ✅
- Clover Location: `VSJ`
- Maps to: `Old San Juan` ✅
- Sheet Column: `BU` (Live Sales Data) ✅

---

## Immediate Fix Options

### Option 1: Manual Update (Quick Fix)
Run the provided script to manually update Jan 28:
```bash
python fix_biscoff_promotion_issue.py
```
This will:
1. Fetch correct count (14) from Clover API
2. Update cell BU16 in sheet "1-28"

### Option 2: Code Fix (Permanent Solution)
1. Update `vm_inventory_updater.py` on VM
2. Fix the quantity counting logic for promotion items
3. Deploy to VM
4. Future runs will count correctly

---

## Test Results

### Debug Script Results
```
Total orders on Jan 28: 74
Orders containing Cheesecake with Biscoff: 11
Line items found: 14
All have quantity: 0 (promotion items)
Counting each as 1 unit: 14 ✅ (matches dashboard)
```

### API Response Sample
```json
{
  "name": "*N* Cheesecake with Biscoff®",
  "quantity": 0,
  "refunded": false,
  "isRevenue": true,
  "categories": ["Cookies", "Promotion (6 Cookies)"]
}
```

---

## Next Steps

1. **Immediate**: Run `fix_biscoff_promotion_issue.py` to fix Jan 28 data
2. **Short-term**: Check `vm_inventory_updater.py` on VM for quantity handling
3. **Long-term**: Apply code fix to handle promotion items correctly
4. **Verify**: Check that future dates count correctly after fix

---

## Files Created

1. `debug_biscoff_jan28.py` - Initial debug script
2. `debug_biscoff_promotion.py` - Promotion item analysis
3. `fix_biscoff_promotion_issue.py` - Manual fix script
4. `BISCOFF_FIX_SUMMARY.md` - Summary document
5. `BISCOFF_DEBUG_COMPLETE.md` - This document

---

**Status**: ✅ Root cause identified, fix ready to apply  
**Date**: January 29, 2026
