# Deployment Instructions for Fixed Script

## Summary of Fixes

The `vm_inventory_updater.py` script has been updated with:

1. **Fixed Cookies & Cream matching**: Now handles both "Cookies & Cream" and "Cookies and Cream" variations
2. **Reliable write method**: Changed from `values.batchUpdate` to `spreadsheet.batchUpdate` with `updateCells` for more reliable writes
3. **Better error handling**: Improved verification and error recovery

## Manual Deployment Steps

Since `gcloud` CLI is not available locally, please run these commands manually:

### Option 1: Using gcloud CLI (if you have it installed)

```bash
gcloud compute scp vm_inventory_updater.py banzo@inventory-updater-vm:/home/banzo/vm_inventory_updater.py --zone=us-central1-a
```

### Option 2: Using SSH and manual copy

1. SSH into the VM:
   ```bash
   gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a
   ```

2. Backup the current script:
   ```bash
   cp /home/banzo/vm_inventory_updater.py /home/banzo/vm_inventory_updater.py.backup
   ```

3. Exit SSH and copy the file from your local machine:
   ```bash
   # From your local machine
   gcloud compute scp vm_inventory_updater.py banzo@inventory-updater-vm:/home/banzo/vm_inventory_updater.py --zone=us-central1-a
   ```

4. SSH back in and verify:
   ```bash
   gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a
   head -20 /home/banzo/vm_inventory_updater.py
   ```

### Option 3: Manual file transfer

If you have access to the VM through another method (Google Cloud Console, etc.), you can:
1. Copy the contents of `vm_inventory_updater.py` from your local machine
2. SSH into the VM
3. Edit the file: `nano /home/banzo/vm_inventory_updater.py`
4. Paste the new contents
5. Save and exit

## Verification

After deployment, the cron job will automatically use the new script on the next run (every 5 minutes). You can verify it's working by:

1. Checking the logs:
   ```bash
   tail -f /home/banzo/inventory.log
   ```

2. Or checking the cron logs:
   ```bash
   tail -f /home/banzo/inventory_cron.log
   ```

## What Changed

### 1. Matching Logic (Lines ~2100-2170)
- Added normalization: "Cookies and Cream" → "Cookies & Cream"
- Added explicit mapping for "Cookies and Cream"
- Added Montehiedra variations for "*C* Cookies and Cream"

### 2. Write Method (Lines ~1587-1647)
- Changed from `values.batchUpdate` to `spreadsheet.batchUpdate` with `updateCells`
- More reliable cell updates that persist correctly
- Better handling of cell references and values

## Expected Behavior After Deployment

- ✅ "Cookies and Cream" from API will correctly match to "C - Cookies & Cream" in sheet
- ✅ Values will persist correctly (no more reverting to 1 or 2)
- ✅ Better error logging for troubleshooting

The script will continue running every 5 minutes automatically via cron.
