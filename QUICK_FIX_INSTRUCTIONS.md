# Quick Fix Instructions

## The Problem
gcloud can't write to its config directory due to permissions.

## Solution Options

### Option 1: Fix Permissions Manually (Easiest)

1. **Open File Explorer** and navigate to:
   ```
   C:\Users\banzo\AppData\Roaming\gcloud
   ```

2. **Right-click** on the `gcloud` folder → **Properties** → **Security** tab

3. Click **Edit** → Select your user → Check **Full Control** → **Apply**

4. **Create the logs folder** if it doesn't exist:
   ```
   C:\Users\banzo\AppData\Roaming\gcloud\logs
   ```

5. **Then run these commands**:
   ```powershell
   cd "e:\prog fold\Drunken cookies\real-time-inventory"
   gcloud compute scp apply_fix_on_vm.py inventory-updater-vm:/home/banzo/ --zone=us-central1-a
   gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && python3 apply_fix_on_vm.py"
   ```

### Option 2: Use PowerShell Script as Admin

1. **Right-click PowerShell** → **Run as Administrator**

2. **Run**:
   ```powershell
   cd "e:\prog fold\Drunken cookies\real-time-inventory"
   .\fix_permissions_simple.ps1
   ```

3. **Then run the gcloud commands** from Option 1

### Option 3: Use Alternative Config Location

Set gcloud to use a different config location:

```powershell
$env:CLOUDSDK_CONFIG = "$env:USERPROFILE\.gcloud"
gcloud compute scp apply_fix_on_vm.py inventory-updater-vm:/home/banzo/ --zone=us-central1-a
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && python3 apply_fix_on_vm.py"
```

---

## What the Fix Does

The `apply_fix_on_vm.py` script will:
1. ✅ Create a backup of `vm_inventory_updater.py`
2. ✅ Apply the promotion quantity fix
3. ✅ Verify the fix was applied
4. ✅ Show you the updated code

After this, future inventory updates will correctly count promotion items (quantity=0) as 1 unit.

---

## Verify It Worked

After applying the fix, verify:

```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="grep -A 5 'FIX FOR PROMOTION ITEMS' /home/banzo/vm_inventory_updater.py"
```

You should see the new code with the promotion fix.
