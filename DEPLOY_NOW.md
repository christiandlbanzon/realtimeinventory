# 🚀 DEPLOY FIXES NOW - Quick Guide

## Current Status
✅ **Script is fixed** (`vm_inventory_updater.py` has both fixes)
❌ **SSH keys have permission issues** (Windows access denied)

## Quick Fix Options

### Option 1: Run PowerShell as Administrator (RECOMMENDED)

1. **Open PowerShell as Administrator** (Right-click → Run as Administrator)

2. **Navigate to project folder:**
   ```powershell
   cd "e:\prog fold\Drunken cookies\real-time-inventory"
   ```

3. **Fix SSH keys:**
   ```powershell
   Remove-Item "$env:USERPROFILE\.ssh\google_compute_engine*" -Force -ErrorAction SilentlyContinue
   & "C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" compute config-ssh
   ```

4. **Deploy the script:**
   ```powershell
   & "C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" compute scp vm_inventory_updater.py inventory-updater-vm:/home/banzo/vm_inventory_updater.py --zone=us-central1-a
   ```

5. **Verify deployment:**
   ```powershell
   & "C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" compute ssh inventory-updater-vm --zone=us-central1-a --command="grep -q 'FIX: Only use fallback' /home/banzo/vm_inventory_updater.py && echo '✅ Fix deployed' || echo '❌ Fix NOT found'"
   ```

---

### Option 2: Use Google Cloud Console (No SSH needed)

1. **Open Google Cloud Console**: https://console.cloud.google.com
2. **Go to Compute Engine → VM instances**
3. **Click on `inventory-updater-vm`**
4. **Click "Edit" or use the serial console**
5. **Copy the fixed script content** from `vm_inventory_updater.py`
6. **Paste into the VM** using the serial console or edit the file directly

---

### Option 3: Use Cloud Shell (Easiest)

1. **Open Google Cloud Shell**: https://shell.cloud.google.com
2. **Upload the file:**
   ```bash
   # In Cloud Shell, click "Upload" button
   # Select: vm_inventory_updater.py
   ```

3. **Deploy to VM:**
   ```bash
   gcloud compute scp vm_inventory_updater.py inventory-updater-vm:/home/banzo/vm_inventory_updater.py --zone=us-central1-a
   ```

4. **Verify:**
   ```bash
   gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="grep -q 'FIX: Only use fallback' /home/banzo/vm_inventory_updater.py && echo '✅ Fix deployed'"
   ```

---

## What Gets Fixed

1. **San Patricio**: Will now use API data (17) instead of fallback (1)
2. **Old San Juan**: Will log warnings if writing suspicious values

## After Deployment

Monitor the logs:
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a
tail -f /home/banzo/inventory_cron.log
```

Look for:
- `✅ Normal API worked for San Patricio` (should see this now)
- `⚠️ LARGE DISCREPANCY DETECTED` (if validation catches issues)

---

**RECOMMENDED: Use Option 1 (PowerShell as Admin)** - It's the fastest if you have admin access.
