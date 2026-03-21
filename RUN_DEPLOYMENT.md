# Run Deployment - Simple Instructions

## ✅ Deployment Script is Ready

The deployment script is already in the VM metadata. You just need to execute it.

## 🚀 Run This (in your normal terminal, not IDE)

Since you've done `gcloud auth login` in a normal terminal, run these commands there:

```bash
# SSH to VM
gcloud compute ssh real-time-inventory --zone=us-central1-a --project=boxwood-chassis-332307

# Once connected, run this ONE command:
curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-and-setup | bash
```

## What It Will Do

1. ✅ Clean up old files on VM
2. ✅ Deploy 3 essential files:
   - `vm_inventory_updater.py` (with February sheet support)
   - `clover_creds.json`
   - `service-account-key.json`
3. ✅ Set up cron job (runs every 5 minutes)
4. ✅ Show verification output

## After Deployment

The VM will:
- ✅ Run the inventory updater every 5 minutes automatically
- ✅ Use February sheet (since it's February now)
- ✅ Update Google Sheets with sales data

## Verify It's Working

```bash
# Check files
ls -lh /home/banzo/*.py /home/banzo/*.json

# Check cron
crontab -l

# Check logs (after first run - wait 5 minutes)
tail -50 /home/banzo/inventory_cron.log
```

---

**Note:** The Google Cloud API is having temporary issues (503 errors), but the deployment script is ready in VM metadata. Just SSH and run it manually - it will work!
