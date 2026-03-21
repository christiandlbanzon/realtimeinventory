# DEPLOY THE FIX NOW - Final Instructions

## Current Status
- ✅ Code fixed locally
- ✅ Tested and verified
- ✅ Backfill completed successfully
- ⏳ **NOT YET DEPLOYED TO VM**

## The Fix File
- **File:** `vm_inventory_updater_fixed.py`
- **Size:** 112,644 characters
- **Contains:** All fixes including `*N* Cheesecake with Biscoff` mapping

## Deployment Methods

### Method 1: Using gcloud scp (RECOMMENDED - Fastest)
```bash
gcloud compute scp vm_inventory_updater_fixed.py banzo@inventory-updater-vm:/home/banzo/vm_inventory_updater.py --zone=us-central1-a
```

### Method 2: SSH and Run Metadata Script
The deployment script is already in VM metadata. Execute it:

```bash
# Step 1: SSH to VM
gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a

# Step 2: Run the deployment script
curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-biscoff-fix | bash
```

### Method 3: SSH and Manual Copy
```bash
# Step 1: SSH to VM
gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a

# Step 2: Backup current file
cd /home/banzo
cp vm_inventory_updater.py vm_inventory_updater.py.backup.$(date +%Y%m%d_%H%M%S)

# Step 3: Copy content from vm_inventory_updater_fixed.py (on your local machine)
# Open vm_inventory_updater_fixed.py, copy all content, then:
nano vm_inventory_updater.py
# Paste content, save (Ctrl+X, Y, Enter)

# Step 4: Set permissions
chmod +x vm_inventory_updater.py
```

## Verification After Deployment

```bash
# SSH to VM
gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a

# Verify the fix is there
grep -c '"*N* Cheesecake with Biscoff"' /home/banzo/vm_inventory_updater.py
# Should return a number > 0

# Check recent logs
tail -50 /home/banzo/inventory_cron.log | grep -i biscoff
```

## What Happens After Deployment

1. **Immediate:** The cron job (runs every 5 minutes) will use the new code
2. **Automatic:** Future sales of `*N* Cheesecake with Biscoff®` will be correctly identified
3. **No Manual Work:** The system will update automatically

## Files Ready for Deployment

- `vm_inventory_updater_fixed.py` - The fixed code ready to deploy
- `deploy_biscoff_fix_via_api.py` - Deployment helper (metadata script added)
- `DEPLOY_NOW_FINAL.md` - This file

## Summary

**The fix is ready but needs manual deployment via SSH/gcloud.**

Once deployed, the VM will automatically use the new mapping logic and correctly identify `*N* Cheesecake with Biscoff®` from Clover API.
