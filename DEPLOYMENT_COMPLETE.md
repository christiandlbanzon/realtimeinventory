# ✅ Deployment Complete - VM Ready to Run

## VM Status

- **VM Name:** `real-time-inventory`
- **Zone:** `us-central1-a`
- **Status:** ✅ Running
- **Deployment Script:** Ready in VM metadata

## 🚀 Execute Deployment (One Command)

SSH to VM and run:

```bash
gcloud compute ssh real-time-inventory --zone=us-central1-a --project=boxwood-chassis-332307

# Once connected, run this ONE command:
curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-and-setup | bash
```

This will:
- ✅ Clean up old files on VM
- ✅ Deploy 3 essential files:
  - `vm_inventory_updater.py` (with February sheet support)
  - `clover_creds.json`
  - `service-account-key.json`
- ✅ Set up cron job (runs every 5 minutes)
- ✅ Show verification output

## 📁 What Will Be on VM (Clean!)

```
/home/banzo/
├── vm_inventory_updater.py      (main script - 113 KB)
├── clover_creds.json            (API credentials)
├── service-account-key.json     (Google credentials)
└── inventory_cron.log           (auto-created log file)
```

**That's it!** Clean and minimal.

## ⏰ Cron Job

After deployment, cron will run every 5 minutes:
```
*/5 * * * * cd /home/banzo && /usr/bin/python3 /home/banzo/vm_inventory_updater.py >> /home/banzo/inventory_cron.log 2>&1
```

## 📊 Features

- ✅ February sheet auto-switching (month >= 2)
- ✅ Biscoff fix included
- ✅ Clover API integration
- ✅ Google Sheets updates
- ✅ Automatic scheduling

## ⚠️ Important: Share February Sheet

Before the VM can update the February sheet, share it with Editor access:

1. Open: https://docs.google.com/spreadsheets/d/1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4/edit
2. Click "Share"
3. Add: `703996360436-compute@developer.gserviceaccount.com`
4. Set permission: **Editor** (not Viewer)
5. Click "Send"

## ✅ Verification

After deployment, verify:

```bash
# Check files
ls -lh /home/banzo/*.py /home/banzo/*.json

# Check cron
crontab -l

# Check logs (after first run)
tail -50 /home/banzo/inventory_cron.log
```

## 🧹 Local Cleanup

Many local files couldn't be deleted (permission issues - may be open). Essential files are kept safe. You can manually delete old files later if needed.

---

**Status:** ✅ Ready to deploy! Just SSH and run the deploy-and-setup command.
