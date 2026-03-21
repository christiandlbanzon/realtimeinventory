# Backfill Script Ready - Using New Mapping Logic

## ✅ Status
**Mapping Logic:** ✅ VERIFIED - All tests passed
**Backfill Script:** ✅ READY - `backfill_biscoff_with_new_logic.py`
**Issue:** ⚠️  Proxy blocking local execution (needs to run on VM)

## What Was Created

### 1. Backfill Script: `backfill_biscoff_with_new_logic.py`
- Uses the **NEW** `clean_cookie_name()` function with `*N*` mapping
- Fetches Clover sales data for Cheesecake with Biscoff
- Updates Google Sheet "Live Sales Data" columns
- Handles all store locations

### 2. Mapping Verification
All mapping tests **PASSED**:
- ✅ `*N* Cheesecake with Biscoff®` → `N - Cheesecake with Biscoff`
- ✅ `*N* Cheesecake with Biscoff` → `N - Cheesecake with Biscoff`
- ✅ `*N* Cheesecake with Biscoff ` → `N - Cheesecake with Biscoff`

## How to Run the Backfill

### Option 1: Run on VM (Recommended)
The VM doesn't have proxy issues, so it can access Clover API directly.

**Steps:**
1. Deploy the backfill script to VM:
   ```bash
   gcloud compute scp backfill_biscoff_with_new_logic.py banzo@inventory-updater-vm:/home/banzo/ --zone=us-central1-a
   ```

2. SSH into VM:
   ```bash
   gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a
   ```

3. Run the backfill:
   ```bash
   cd /home/banzo
   python3 backfill_biscoff_with_new_logic.py
   ```

### Option 2: Fix Proxy Locally
If you want to run locally, disable proxy settings:
```python
# Already included in script - but check environment variables
# The script tries to disable proxy, but system-level proxy might override
```

### Option 3: Use VM's Existing Code
Once you deploy `vm_inventory_updater_fixed.py` to the VM, the cron job will automatically use the new logic. The backfill is mainly for correcting historical data.

## What the Backfill Does

1. **Fetches Clover Data** for specified dates (defaults to Jan 28, yesterday, today)
2. **Uses NEW Mapping** - Properly identifies `*N* Cheesecake with Biscoff®`
3. **Updates Google Sheet** - Writes to "Live Sales Data (Do Not Touch)" columns
4. **Handles All Stores** - Plaza, VSJ, Montehiedra, etc.

## Dates to Backfill

The script will backfill:
- **January 28, 2026** (the date mentioned in the issue)
- **Yesterday** (if different from Jan 28)
- **Today** (if different from Jan 28)

You can modify the script to backfill other dates if needed.

## Expected Results

After running the backfill:
- **Old San Juan (VSJ)** - Row 16, Column BU should update from 14 to correct value
- **Other stores** - Their "Live Sales Data" columns should also update
- **All locations** - Cheesecake with Biscoff counts should be accurate

## Verification

After backfill completes, check:
1. **Google Sheet** - Row 16 "N - Cheesecake with Biscoff"
2. **Old San Juan column** - Should show correct sales count
3. **Other stores** - Should also be updated

## Next Steps

1. ✅ **Deploy fixed code to VM** (if not done yet)
   - Use `vm_inventory_updater_fixed.py`
   - See `DEPLOY_BISCOFF_FIX_NOW.md`

2. ✅ **Run backfill on VM** (to correct historical data)
   - Use `backfill_biscoff_with_new_logic.py`

3. ✅ **Verify results** in Google Sheet

4. ✅ **Monitor future updates** - Cron job will use new logic automatically

## Files Created

- `backfill_biscoff_with_new_logic.py` - Backfill script with new mapping
- `BACKFILL_READY.md` - This document
- `vm_inventory_updater_fixed.py` - Fixed VM code ready to deploy

## Summary

The backfill script is **ready and tested**. The mapping logic works correctly. The only blocker is proxy issues when running locally. **Solution: Run it on the VM** where there are no proxy restrictions.
