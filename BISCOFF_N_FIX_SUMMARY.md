# Fix for N - Cheesecake with Biscoff Identification Issue

## Problem
The Clover API returns `*N* Cheesecake with Biscoff®` but the code was not properly mapping it to `N - Cheesecake with Biscoff` in the Google Sheet. This caused the item to show 0 sales instead of the actual count.

## Root Cause
The `clean_cookie_name()` function in `deploy_temp.sh` (which becomes `vm_inventory_updater.py` on the VM) had mappings for:
- `*H* Cheesecake with Biscoff` → `H - Cheesecake with Biscoff`
- `Cheesecake with Biscoff` → `H - Cheesecake with Biscoff`

But it was **missing** mappings for:
- `*N* Cheesecake with Biscoff` → `N - Cheesecake with Biscoff`
- `*N* Cheesecake with Biscoff®` → `N - Cheesecake with Biscoff` (with registered symbol)
- `*N* Cheesecake with Biscoff ` → `N - Cheesecake with Biscoff` (with trailing space)

## Solution Applied

### 1. Added to `montehiedra_mapping` dictionary (line ~1946)
```python
"*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff",
"*N* Cheesecake with Biscoff ": "N - Cheesecake with Biscoff",
```

### 2. Added to `name_mapping` dictionary - first section (line ~2009)
```python
"*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff",
```

### 3. Added to `name_mapping` dictionary - trailing spaces section (line ~2027)
```python
"*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff",
"*N* Cheesecake with Biscoff ": "N - Cheesecake with Biscoff",
```

### 4. Fixed fallback mapping (line ~2041)
Changed from:
```python
"Cheesecake with Biscoff": "H - Cheesecake with Biscoff",
```
To:
```python
"Cheesecake with Biscoff": "N - Cheesecake with Biscoff",  # Changed from H to N - this is the correct mapping
```

### 5. Added special character handling (line ~2065)
```python
"*N* Cheesecake with Biscoff®": "N - Cheesecake with Biscoff",  # Handle registered symbol
"*N* Cheesecake with Biscoff ": "N - Cheesecake with Biscoff",  # Handle trailing space
```

## Files Modified
- `deploy_temp.sh` - Contains the Python code that gets deployed to the VM

## Verification

To verify the fix works:

1. **Check Clover API returns `*N*` prefix:**
   ```python
   # The API returns: "*N* Cheesecake with Biscoff®"
   ```

2. **Check the mapping function:**
   ```python
   clean_cookie_name("*N* Cheesecake with Biscoff®")
   # Should return: "N - Cheesecake with Biscoff"
   ```

3. **Check Google Sheet:**
   - Row 16 should be "N - Cheesecake with Biscoff"
   - The code should now properly update this row with sales data

## Next Steps

1. **Deploy the fixed code to VM:**
   ```bash
   # Extract Python from deploy_temp.sh and deploy
   gcloud compute scp deploy_temp.sh inventory-updater-vm:/home/banzo/ --zone=us-central1-a
   # Then SSH and extract/run the Python code
   ```

2. **Or manually update vm_inventory_updater.py on VM:**
   - The Python code is embedded in `deploy_temp.sh` starting at line 13
   - Extract it and update `/home/banzo/vm_inventory_updater.py` on the VM

3. **Test the fix:**
   - Wait for the next cron run (every 5 minutes)
   - Check that `N - Cheesecake with Biscoff` row gets updated with sales data
   - Verify logs show proper identification

## Notes

- The `*H*` mapping is kept for other locations that might use that prefix
- The fix handles multiple variations:
  - `*N* Cheesecake with Biscoff` (no special chars)
  - `*N* Cheesecake with Biscoff®` (with registered symbol)
  - `*N* Cheesecake with Biscoff ` (with trailing space)
  - `Cheesecake with Biscoff` (fallback, no prefix)

## Status
✅ **FIXED** - All mappings added to `deploy_temp.sh`
⏳ **PENDING** - Deployment to VM needed
⏳ **PENDING** - Verification testing needed
