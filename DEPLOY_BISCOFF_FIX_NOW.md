# Deploy Biscoff Fix - Instructions

## Status
✅ **Code Fixed** - The `*N* Cheesecake with Biscoff` mapping has been added to `deploy_temp.sh`
✅ **Code Extracted** - Python code extracted to `vm_inventory_updater_fixed.py`
⏳ **Pending Deployment** - Needs to be copied to VM

## The Problem
The Clover API returns `*N* Cheesecake with Biscoff®` but the VM code was missing the mapping to convert it to `N - Cheesecake with Biscoff` in the Google Sheet. This caused the item to show 0 or incorrect values.

## The Fix
Added mappings in `clean_cookie_name()` function:
- `"*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff"`
- `"*N* Cheesecake with Biscoff ": "N - Cheesecake with Biscoff"` (with trailing space)
- `"*N* Cheesecake with Biscoff®": "N - Cheesecake with Biscoff"` (with registered symbol)
- Changed fallback: `"Cheesecake with Biscoff": "N - Cheesecake with Biscoff"` (was H, now N)

## Deployment Options

### Option 1: Using gcloud CLI (Recommended)
```bash
gcloud compute scp vm_inventory_updater_fixed.py banzo@inventory-updater-vm:/home/banzo/vm_inventory_updater.py --zone=us-central1-a
```

### Option 2: Using SSH and manual copy
1. SSH into VM:
   ```bash
   gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a
   ```

2. Backup current file:
   ```bash
   cd /home/banzo
   cp vm_inventory_updater.py vm_inventory_updater.py.backup.$(date +%Y%m%d_%H%M%S)
   ```

3. Exit SSH and copy file from your local machine:
   ```bash
   # From your local machine (PowerShell)
   gcloud compute scp vm_inventory_updater_fixed.py banzo@inventory-updater-vm:/home/banzo/vm_inventory_updater.py --zone=us-central1-a
   ```

### Option 3: Direct SCP (if you have SSH access configured)
```bash
scp vm_inventory_updater_fixed.py banzo@34.69.171.53:/home/banzo/vm_inventory_updater.py
```

### Option 4: Manual file edit via SSH
1. SSH into VM:
   ```bash
   gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a
   ```

2. Backup current file:
   ```bash
   cd /home/banzo
   cp vm_inventory_updater.py vm_inventory_updater.py.backup
   ```

3. Open file for editing:
   ```bash
   nano vm_inventory_updater.py
   ```

4. Copy contents from `vm_inventory_updater_fixed.py` (on your local machine) and paste into nano

5. Save and exit: `Ctrl+X`, then `Y`, then `Enter`

## Verification

After deployment, verify the fix is working:

### 1. Check the file on VM has the fix:
```bash
gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a --command="grep -c '\"\\*N\\* Cheesecake with Biscoff\"' /home/banzo/vm_inventory_updater.py"
```
Should return a number > 0 (indicating the mapping exists)

### 2. Check logs after next cron run:
```bash
gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a --command="tail -100 /home/banzo/inventory_cron.log | grep -i biscoff"
```

### 3. Check Google Sheet:
- Wait for the next cron run (every 5 minutes)
- Check row 16 "N - Cheesecake with Biscoff" 
- The "Live Sales Data" column should update with actual sales

## Files Created
- `vm_inventory_updater_fixed.py` - The fixed Python code ready to deploy
- `BISCOFF_N_FIX_SUMMARY.md` - Detailed documentation of the fix
- `test_biscoff_n_mapping.py` - Test script (all tests passed ✅)

## Important Notes
- The cron job runs every 5 minutes automatically
- After deployment, the fix will take effect on the next cron run
- No VM restart needed - just replace the file
- The old code will be backed up automatically if you use the backup commands above

## Troubleshooting

If the fix doesn't work after deployment:

1. **Check file was updated:**
   ```bash
   gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a --command="head -20 /home/banzo/vm_inventory_updater.py"
   ```

2. **Check for errors in logs:**
   ```bash
   gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a --command="tail -50 /home/banzo/inventory_cron.log"
   ```

3. **Manually test the mapping:**
   ```bash
   gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a
   cd /home/banzo
   python3 -c "from vm_inventory_updater import clean_cookie_name; print(clean_cookie_name('*N* Cheesecake with Biscoff®'))"
   ```
   Should output: `N - Cheesecake with Biscoff`
