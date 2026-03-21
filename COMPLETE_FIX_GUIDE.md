# Complete Fix Guide - Cheesecake with Biscoff Promotion Issue

## Summary

This guide provides **three solutions** to fix the Cheesecake with Biscoff issue on January 28:
1. ✅ Check actual VM code
2. ✅ Create patch file for VM code fix
3. ✅ Manually update Jan 28 data

---

## 1. Check Actual VM Code

### Script Created: `check_vm_code.py`

**Purpose**: Check how quantity is currently handled in the VM code

**Usage**:
```bash
python check_vm_code.py
```

**What it does**:
- Connects to VM via SSH
- Checks if `vm_inventory_updater.py` exists
- Searches for quantity handling code
- Shows relevant code sections

**Note**: SSH commands may timeout from local machine. Alternative: SSH directly to VM and run:
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a
grep -n "quantity" /home/banzo/vm_inventory_updater.py | head -20
sed -n "870,880p" /home/banzo/vm_inventory_updater.py
```

---

## 2. Patch File for VM Code Fix

### Files Created:
- `fix_promotion_quantity.patch` - Standard patch file
- `apply_promotion_fix.py` - Python script to apply fix

### The Fix

**Problem**: Promotion items have `quantity: 0` but should count as 1 unit

**Solution**: Check if quantity is 0, and if so, count as 1 unit

**Code Change**:
```python
# OLD CODE (line ~874):
quantity = 1  # Each line item = 1 unit

# NEW CODE:
api_quantity = item.get('quantity', 0)
if api_quantity == 0:
    # Promotion items have quantity=0 but each line item = 1 unit sold
    quantity = 1
else:
    # Normal items: convert from millis to units (1000 millis = 1 unit)
    quantity = int(api_quantity / 1000) if api_quantity > 0 else 1

# Ensure minimum of 1 unit per line item (safety check)
quantity = max(quantity, 1)
```

### Apply Patch on VM

**Option A: Using patch file**
```bash
# On VM:
cd /home/banzo
# Copy patch file to VM first
patch -p0 < fix_promotion_quantity.patch
```

**Option B: Using Python script**
```bash
# On VM:
cd /home/banzo
python3 apply_promotion_fix.py vm_inventory_updater.py
```

**Option C: Manual edit**
1. SSH to VM: `gcloud compute ssh inventory-updater-vm --zone=us-central1-a`
2. Edit file: `nano /home/banzo/vm_inventory_updater.py`
3. Find line ~874 (search for "quantity = 1")
4. Replace with the new code above
5. Save and exit

### Verify Fix

After applying, verify the change:
```bash
# On VM:
grep -A 10 "FIX FOR PROMOTION" /home/banzo/vm_inventory_updater.py
```

---

## 3. Manually Update Jan 28 Data

### Scripts Created:
- `update_jan28_biscoff.py` - Interactive version (asks for confirmation)
- `update_jan28_biscoff_auto.py` - Automatic version (no confirmation)

### Usage

**Automatic (recommended)**:
```bash
python update_jan28_biscoff_auto.py
```

**Interactive**:
```bash
python update_jan28_biscoff.py
```

### What It Does

1. **Fetches data from Clover API**
   - Gets all orders for Jan 28 from VSJ
   - Finds Cheesecake with Biscoff line items
   - **Correctly counts promotion items** (quantity=0 → count as 1)

2. **Updates Google Sheet**
   - Sheet: January Mall Pars_2026
   - Tab: 1-28
   - Cell: BU16 (Old San Juan, Cheesecake with Biscoff, Live Sales Data)
   - Value: Updates to correct count (14)

### Expected Output

```
================================================================================
UPDATE JANUARY 28 - CHEESECAKE WITH BISCOFF
================================================================================

Fetching Cheesecake with Biscoff sales for January 28...
Found 14 Cheesecake with Biscoff sold on Jan 28
Updating Google Sheet...
Current value: 0
✅ Updated BU16 from 0 to 14

✅ UPDATE COMPLETE!
Cheesecake with Biscoff for Jan 28 updated to 14
```

---

## Complete Solution Steps

### Step 1: Immediate Fix (Update Jan 28 Data)
```bash
python update_jan28_biscoff_auto.py
```
✅ This fixes the Jan 28 data immediately

### Step 2: Check VM Code
```bash
# Option A: From local machine (may timeout)
python check_vm_code.py

# Option B: SSH directly to VM
gcloud compute ssh inventory-updater-vm --zone=us-central1-a
grep -n "quantity" /home/banzo/vm_inventory_updater.py
```

### Step 3: Apply Code Fix to VM
```bash
# Copy files to VM
gcloud compute scp apply_promotion_fix.py inventory-updater-vm:/home/banzo/ --zone=us-central1-a
gcloud compute scp vm_inventory_updater.py inventory-updater-vm:/home/banzo/ --zone=us-central1-a

# SSH to VM
gcloud compute ssh inventory-updater-vm --zone=us-central1-a

# On VM:
cd /home/banzo
python3 apply_promotion_fix.py vm_inventory_updater.py

# Verify fix
grep -A 5 "FIX FOR PROMOTION" vm_inventory_updater.py
```

### Step 4: Test Fix
After applying the fix, wait for the next cron run (every 5 minutes) or manually test:
```bash
# On VM:
cd /home/banzo
export INVENTORY_SHEET_ID=1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno
/home/banzo/venv/bin/python vm_inventory_updater.py
```

---

## Files Summary

| File | Purpose |
|------|---------|
| `check_vm_code.py` | Check VM code for quantity handling |
| `fix_promotion_quantity.patch` | Standard patch file for the fix |
| `apply_promotion_fix.py` | Python script to apply fix automatically |
| `update_jan28_biscoff.py` | Interactive script to update Jan 28 data |
| `update_jan28_biscoff_auto.py` | Automatic script to update Jan 28 data |
| `COMPLETE_FIX_GUIDE.md` | This guide |

---

## Verification

After applying all fixes:

1. **Jan 28 Data**: Should show 14 in cell BU16 ✅
2. **Future Dates**: Should correctly count promotion items ✅
3. **VM Logs**: Check for correct counting:
   ```bash
   tail -100 /home/banzo/inventory_cron.log | grep -i biscoff
   ```

---

## Troubleshooting

### If update script fails:
- Check credentials: `clover_creds.json` and `service-account-key.json`
- Verify sheet ID: Check `INVENTORY_SHEET_ID` environment variable
- Check network: Ensure API access works

### If patch doesn't apply:
- Check file structure matches expected pattern
- Apply manually using the code provided
- Verify backup was created before applying

### If VM code check times out:
- SSH directly to VM instead
- Check VM is running: `gcloud compute instances describe inventory-updater-vm --zone=us-central1-a`

---

**Status**: ✅ All three solutions ready  
**Date**: January 29, 2026
