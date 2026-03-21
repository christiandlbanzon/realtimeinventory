# Deploy February Sheet Update

## ✅ Code Updated

The code has been updated to automatically switch to the February sheet when February arrives.

### Changes Made:
- **January sheet:** `1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE` (used for month 1)
- **February+ sheet:** `1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4` (used for months 2-12)

The code automatically detects the current month and uses the appropriate sheet.

## 🚀 Deploy to VM

Run this command in PowerShell:

```powershell
cd "e:\prog fold\Drunken cookies\real-time-inventory"
gcloud compute scp vm_inventory_updater_fixed.py banzo@inventory-updater-vm:/home/banzo/vm_inventory_updater.py --zone=us-central1-a
```

## ✅ Verify Deployment

After deployment, verify the February sheet ID is in the code:

```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command='grep -c "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4" /home/banzo/vm_inventory_updater.py'
```

Expected output: A number > 0 (e.g., `1`)

## 📅 How It Works

- **January 1-31:** Uses January sheet (`1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE`)
- **February 1+:** Automatically switches to February sheet (`1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4`)
- **March-December:** Continues using February sheet (or you can add more months later)

The switch happens automatically based on the current date when the cron job runs.

## ⏰ Next Steps

1. Deploy the file using the command above
2. The cron job (runs every 5 minutes) will automatically use the correct sheet
3. On February 1st, it will automatically switch to the February sheet
4. No manual intervention needed!
