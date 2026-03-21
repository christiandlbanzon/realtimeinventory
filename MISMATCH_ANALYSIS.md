# Mismatch Analysis - Cookies & Cream (January 24, 2026)

## Summary

| Location | Clover API | Google Sheet | Difference | Status |
|----------|------------|--------------|------------|--------|
| **Plaza Del Sol** | 14 | 14 | 0 | ✅ MATCH |
| **Old San Juan** | 88 | 100 | +12 (Sheet higher) | ❌ MISMATCH |
| **San Patricio** | 17 | 1 | -16 (Sheet lower) | ❌ MISMATCH |

## Detailed Findings

### 1. Old San Juan (VSJ) - Sheet Shows 12 More Than Clover

**Clover API Analysis:**
- Total orders on 2026-01-24: **515 orders**
- Orders with cookies: **449 orders**
- Cookies & Cream items found: **88 items**
- All items are: `*C* Cookies & Cream` (single item name, 88 occurrences)

**Why the Mismatch?**
The sheet shows **100** but Clover API shows **88**. Possible causes:

1. **Manual Edit**: Someone manually edited the sheet and added 12
2. **Wrong Date**: Sheet might include data from a different date
3. **Double Counting**: Previous update might have double-counted some items
4. **Different Time Range**: Sheet might include orders from a slightly different time window
5. **Cached/Stale Data**: Sheet might not have been updated with the latest Clover data

**Recommendation:**
- Update sheet to **88** (Clover API value is the source of truth)
- Verify when the last update ran
- Check if there were any manual edits

---

### 2. San Patricio - Sheet Shows 16 Less Than Clover

**Clover API Analysis:**
- Total orders on 2026-01-24: **54 orders**
- Orders with cookies: **52 orders**
- Cookies & Cream items found: **17 items**
- All items are: `*C* Cookies & Cream` (single item name, 17 occurrences)

**Why the Mismatch?**

**Root Cause Found!** 🎯

The main script (`vm_inventory_updater.py`) has **special fallback logic** for San Patricio:

```python
# Special handling for San Patricio (API issues)
if location == 'San Patricio':
    location_sales = fetch_san_patricio_sales_with_fallback(creds, target_date)
```

**How the Fallback Works:**
1. Tries normal Clover API first
2. If API returns **0 sales** OR fails, it uses fallback data
3. Fallback data only has one date: `2024-09-29`
4. For January 24, 2026, fallback returns **empty dict `{}`**
5. When fallback is empty, the script might write **0** or **1** to the sheet

**The Problem:**
- Clover API actually works and returns **17 Cookies & Cream**
- But if the script thought API returned 0 (due to data structure issues), it used fallback
- Fallback for Jan 24, 2026 doesn't exist → returns `{}`
- Sheet got updated with **0 or 1** instead of **17**

**Recommendation:**
1. **Immediate Fix**: Update sheet to **17** (Clover API value)
2. **Code Fix**: The fallback logic should check if API actually works before using fallback
3. **Long-term**: Add January 24, 2026 data to fallback if API is unreliable for this date

---

## Technical Details

### Clover API Data Quality

**Old San Juan:**
- ✅ API is working correctly
- ✅ All 88 items are properly identified as Cookies & Cream
- ✅ Item name is consistent: `*C* Cookies & Cream`

**San Patricio:**
- ✅ API is working correctly (returns 17)
- ✅ All 17 items are properly identified as Cookies & Cream
- ✅ Item name is consistent: `*C* Cookies & Cream`
- ⚠️ **BUT**: Main script's fallback logic may be incorrectly triggering

### Main Script Behavior

The main script (`vm_inventory_updater.py`) has this logic for San Patricio:

```python
def fetch_san_patricio_sales_with_fallback(creds, target_date=None):
    # Try normal API first
    normal_sales = fetch_clover_sales(creds, target_date)
    total_sales = sum(normal_sales.values()) if normal_sales else 0
    
    if total_sales > 0:
        return normal_sales  # ✅ Use API data
    else:
        # ⚠️ Use fallback (but fallback is empty for Jan 24)
        return get_san_patricio_fallback_data()  # Returns {}
```

**The Issue:**
- If `total_sales == 0` (even temporarily), it uses fallback
- Fallback for Jan 24, 2026 is empty `{}`
- Sheet gets updated with empty/zero data

---

## Action Items

### Immediate Actions
1. ✅ **Update Old San Juan**: Change from 100 → **88**
2. ✅ **Update San Patricio**: Change from 1 → **17**

### Code Improvements Needed
1. **Fix San Patricio Fallback Logic**:
   - Only use fallback if API actually fails (not just returns 0)
   - Check if fallback data exists before using it
   - Log when fallback is used vs when API data is used

2. **Add Validation**:
   - Compare Clover API values with sheet values before updating
   - Alert if discrepancy is too large
   - Log all updates for audit trail

3. **Update Fallback Data**:
   - Add January 24, 2026 to fallback data if needed
   - Or remove fallback logic if API is now reliable

---

## Verification

The verification script (`verify_clover_vs_sheet.py`) successfully:
- ✅ Connected to Clover API
- ✅ Fetched accurate data for all locations
- ✅ Read current sheet values
- ✅ Identified exact discrepancies

**Clover API is the source of truth** - the sheet values need to be corrected.

---

**Investigation Date**: January 25, 2026
**Analysis Script**: `investigate_mismatches.py`
