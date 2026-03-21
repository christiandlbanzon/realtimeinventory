# ✅ New VM Created Successfully!

## VM Information

- **VM Name:** `inventory-updater-vm-new`
- **Zone:** `us-central1-a`
- **Project:** `boxwood-chassis-332307`
- **Status:** ✅ Running
- **Machine Type:** e2-micro (smallest/cheapest)

## ✅ What's Ready

1. **VM Created** - Fresh Debian 12 instance
2. **Python Installed** - Python 3 and pip ready
3. **Dependencies Ready** - Google APIs, requests, etc. installed
4. **Deployment Scripts** - Ready in VM metadata

## 🚀 Deploy Files (Run These Commands)

SSH to the VM:

```bash
gcloud compute ssh inventory-updater-vm-new --zone=us-central1-a --project=boxwood-chassis-332307
```

Once connected, run:

```bash
# Deploy all files
curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-files | bash

# Set up cron job (runs every 5 minutes)
curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/setup-cron | bash

# Verify everything is deployed
ls -lh /home/banzo/
crontab -l
```

## 📁 Files That Will Be Deployed

- ✅ `vm_inventory_updater.py` - Main script (with February sheet support)
- ✅ `clover_creds.json` - Clover API credentials
- ✅ `service-account-key.json` - Google Sheets API credentials

## ⏰ Cron Job

After setup, the cron job will run every 5 minutes:
```
*/5 * * * * cd /home/banzo && /usr/bin/python3 /home/banzo/vm_inventory_updater.py >> /home/banzo/inventory_cron.log 2>&1
```

## 📊 Features

- ✅ February sheet auto-switching
- ✅ Biscoff fix included
- ✅ Clover API integration
- ✅ Google Sheets updates
- ✅ Automatic cron scheduling

## 🧹 Cleanup Note

Some files couldn't be deleted due to permission issues (they may be open). You can manually delete old files if needed. The essential files are kept safe.
