# Step-by-Step: Apply VM Fix

## Current Status ✅
- ✅ All Jan 28 stores fixed
- ✅ Fix script created (`apply_fix_on_vm.py`)
- ⚠️ gcloud has permission issues

## Solution: Fix gcloud Permissions First

### Step 1: Fix gcloud Permissions (Run as Administrator)

**Option A: Using PowerShell (Run as Admin)**
```powershell
# Right-click PowerShell → Run as Administrator
cd "e:\prog fold\Drunken cookies\real-time-inventory"
.\fix_permissions_simple.ps1
```

**Option B: Manual Fix**
1. Open File Explorer
2. Go to: `C:\Users\banzo\AppData\Roaming\gcloud`
3. Right-click → Properties → Security → Edit
4. Select your user → Check "Full Control" → Apply
5. Create folder: `C:\Users\banzo\AppData\Roaming\gcloud\logs`

### Step 2: Copy Fix Script to VM

```powershell
cd "e:\prog fold\Drunken cookies\real-time-inventory"
gcloud compute scp apply_fix_on_vm.py inventory-updater-vm:/home/banzo/ --zone=us-central1-a
```

### Step 3: Run Fix on VM

**Option A: One command**
```powershell
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && python3 apply_fix_on_vm.py"
```

**Option B: SSH and run manually**
```powershell
gcloud compute ssh inventory-updater-vm --zone=us-central1-a
# Then on VM:
cd /home/banzo
python3 apply_fix_on_vm.py
```

### Step 4: Verify Fix

```powershell
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="grep -A 5 'FIX FOR PROMOTION ITEMS' /home/banzo/vm_inventory_updater.py"
```

---

## Alternative: If gcloud Still Doesn't Work

If gcloud permissions can't be fixed, you can:

1. **Copy the script content manually**:
   - Open `apply_fix_on_vm.py` 
   - Copy all its content
   - SSH to VM: `gcloud compute ssh inventory-updater-vm --zone=us-central1-a`
   - Create file: `nano /home/banzo/apply_fix_on_vm.py`
   - Paste content, save (Ctrl+O, Enter, Ctrl+X)
   - Run: `python3 /home/banzo/apply_fix_on_vm.py`

2. **Or apply fix manually**:
   - SSH to VM
   - Edit: `nano /home/banzo/vm_inventory_updater.py`
   - Find line ~874 with `quantity = 1`
   - Replace with code from `fix_promotion_quantity.patch`
   - Save and exit

---

## What Gets Fixed

The fix ensures that promotion items (which have `quantity: 0` in Clover API) are counted as 1 unit instead of 0.

**Before**: Promotion items → 0 counted  
**After**: Promotion items → 1 counted ✅

This will fix Cheesecake with Biscoff and any other items sold in promotions for all future dates.

---

## Files Ready

- ✅ `apply_fix_on_vm.py` - The fix script
- ✅ `fix_permissions_simple.ps1` - Permission fix script
- ✅ `QUICK_FIX_INSTRUCTIONS.md` - Quick reference
- ✅ `STEP_BY_STEP_VM_FIX.md` - This file
