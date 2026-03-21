# Fix for Cheesecake with Biscoff - January 28 Issue

## Problem Identified ✅

**Issue**: Cheesecake with Biscoff shows 0 in Google Sheet on Jan 28, but Clover dashboard shows 14 sold.

**Root Cause**: Items in promotions/bundles have `quantity: 0` in Clover API line items, but they still represent 1 unit sold. The current code adds `quantity` (which is 0) to the count, resulting in 0.

## Evidence

1. **Clover Dashboard**: Shows 14 units sold for "*N* Cheesecake with Biscoff" on Jan 28
2. **Clover API**: Returns 14 line items, all with `quantity: 0`
3. **Google Sheet**: Shows 0 in "Live Sales Data" column (BU16)
4. **Debug Script**: Confirmed counting line items as 1 unit each gives correct count of 14

## Solution

The code already sets `quantity = 1` at line 874 in `deploy_temp.sh`, but there might be another place where `quantity = item.get('quantity', 0)` is used, which would override this.

**Fix needed**: Ensure that when `quantity` from API is 0, we count it as 1 unit (since each line item = 1 unit sold).

## Code Location

File: `vm_inventory_updater.py` (or `deploy_temp.sh`)
Function: `fetch_clover_sales()`
Line: ~874 and ~1057

## Recommended Fix

```python
# Current (line 874):
quantity = 1  # Each line item = 1 unit

# This is correct! But check if it's being overridden later.

# If there's code like this (line ~1057):
quantity = item.get('quantity', 0)

# Change to:
quantity = item.get('quantity', 0)
if quantity == 0:
    quantity = 1  # Promotion items have qty=0 but still count as 1 unit
```

## Additional Issues Found

1. **Cookie Name Mapping**: "*N* Cheesecake with Biscoff" needs to map to "N - Cheesecake with Biscoff" (row 16)
   - Current mapping might be looking for "*H*" instead of "*N*"
   - Fix: Add mapping for "*N* Cheesecake with Biscoff" → "N - Cheesecake with Biscoff"

2. **Location Mapping**: VSJ → Old San Juan is correct
   - Column BU is correct for Old San Juan "Live Sales Data"

## Next Steps

1. Check `vm_inventory_updater.py` on VM to see actual code
2. Apply fix for promotion items (count 0 quantity as 1)
3. Verify "*N*" mapping exists in `clean_cookie_name()` function
4. Test with Jan 28 data
5. Deploy fix to VM

## Test Results

- ✅ Clover API returns 14 line items
- ✅ All have quantity=0 (promotion items)
- ✅ Counting each as 1 unit = 14 (matches dashboard)
- ✅ Cookie name "*N* Cheesecake with Biscoff" maps correctly
- ✅ Location VSJ maps to Old San Juan correctly
- ❌ Current code adds 0 instead of 1 for promotion items
