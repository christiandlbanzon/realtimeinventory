# Instructions to Apply VM Code Fix

## Summary

✅ **All stores fixed for Jan 28:**
- Plaza Las Americas: 0 → 1 (BJ16)
- Plaza del Sol: 0 → 3 (T16)
- San Patricio: 0 → 3 (F16)
- Old San Juan: 14 (BU16) - already correct
- Montehiedra: 0 → 1 (AH16)
- Plaza Carolina: 0 (no sales)

Now we need to apply the code fix to the VM so future dates count correctly.

---

## Method 1: Copy Script to VM (Recommended)

### Step 1: Copy the fix script to VM
```bash
gcloud compute scp apply_fix_on_vm.py inventory-updater-vm:/home/banzo/ --zone=us-central1-a
```

### Step 2: SSH to VM
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a
```

### Step 3: Run the fix script
```bash
cd /home/banzo
python3 apply_fix_on_vm.py
```

### Step 4: Verify
```bash
grep -A 10 "FIX FOR PROMOTION ITEMS" vm_inventory_updater.py
```

---

## Method 2: Manual Edit

### Step 1: SSH to VM
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a
```

### Step 2: Create backup
```bash
cd /home/banzo
cp vm_inventory_updater.py vm_inventory_updater.py.backup.$(date +%Y%m%d_%H%M%S)
```

### Step 3: Edit file
```bash
nano vm_inventory_updater.py
```

### Step 4: Find and replace
Search for (around line 874):
```python
quantity = 1  # Each line item = 1 unit
```

Replace with:
```python
# FIX FOR PROMOTION ITEMS: Items in promotions have quantity=0 but still count as 1 unit
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

### Step 5: Save and verify
- Save file (Ctrl+O, Enter, Ctrl+X in nano)
- Verify: `grep -A 5 "FIX FOR PROMOTION ITEMS" vm_inventory_updater.py`

---

## Method 3: Using Patch File

### Step 1: Copy patch file to VM
```bash
gcloud compute scp fix_promotion_quantity.patch inventory-updater-vm:/home/banzo/ --zone=us-central1-a
```

### Step 2: SSH to VM and apply
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a
cd /home/banzo
patch -p0 < fix_promotion_quantity.patch
```

---

## Verification After Fix

### Check fix is applied:
```bash
grep "FIX FOR PROMOTION ITEMS" /home/banzo/vm_inventory_updater.py
```

### Test the script:
```bash
cd /home/banzo
export INVENTORY_SHEET_ID=1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno
/home/banzo/venv/bin/python vm_inventory_updater.py
```

### Check logs:
```bash
tail -50 /home/banzo/inventory_cron.log | grep -i biscoff
```

---

## What the Fix Does

**Before**: Promotion items with `quantity: 0` were counted as 0
**After**: Promotion items with `quantity: 0` are counted as 1 unit

This ensures that items sold as part of promotions/bundles are correctly counted in the inventory.

---

## Files Available

1. `apply_fix_on_vm.py` - Standalone script to apply fix (copy to VM and run)
2. `fix_promotion_quantity.patch` - Standard patch file
3. `apply_promotion_fix.py` - Alternative Python script
4. `APPLY_VM_FIX_INSTRUCTIONS.md` - This file

---

**Status**: ✅ All stores fixed for Jan 28  
**Next**: Apply VM code fix using one of the methods above
