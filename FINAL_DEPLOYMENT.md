# ✅ Clean Deployment Ready

## 🎯 What We Have Full Control Over

✅ **New VM:** `inventory-updater-vm-new`
- Fresh, clean Debian 12 instance
- Only essential files will be deployed
- No old/debug files

✅ **Clean Deployment Script**
- Deploys only 3 essential files
- Cleans up old backups/logs on VM
- Sets up cron job

## 📦 Files That Will Be on VM (Clean!)

Only these 3 files will be deployed:

1. **`vm_inventory_updater.py`** - Main script (113 KB)
   - February sheet support
   - Biscoff fix included
   - All features working

2. **`clover_creds.json`** - Clover API credentials (939 bytes)

3. **`service-account-key.json`** - Google Sheets API credentials (2.4 KB)

**Total:** ~116 KB - Very clean and minimal!

## 🚀 Deploy to VM (One Command)

SSH to VM and run:

```bash
gcloud compute ssh inventory-updater-vm-new --zone=us-central1-a --project=boxwood-chassis-332307

# Once connected, run this ONE command:
curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-clean | bash
```

This will:
- ✅ Clean up any old files on VM
- ✅ Deploy only the 3 essential files
- ✅ Set up cron job (runs every 5 minutes)
- ✅ Show you what's on the VM

## 📊 VM Will Have

```
/home/banzo/
├── vm_inventory_updater.py      (main script)
├── clover_creds.json            (API credentials)
├── service-account-key.json     (Google credentials)
└── inventory_cron.log           (log file, auto-created)
```

**That's it!** Clean and minimal.

## ⏰ Cron Job

After deployment, cron will run every 5 minutes:
```
*/5 * * * * cd /home/banzo && /usr/bin/python3 /home/banzo/vm_inventory_updater.py >> /home/banzo/inventory_cron.log 2>&1
```

## 🧹 Local Cleanup Note

Some local files couldn't be deleted (permission issues - may be open). But the VM will be completely clean with only essential files.

## ✅ Summary

- ✅ VM created: `inventory-updater-vm-new`
- ✅ Clean deployment script ready
- ✅ Only 3 essential files will be deployed
- ✅ VM will be clean and minimal
- ✅ Full control over what's deployed

**Ready to deploy!** Just SSH and run the deploy-clean command.
