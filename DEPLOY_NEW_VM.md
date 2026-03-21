# ✅ New VM Created: inventory-updater-vm-new

## VM Details
- **Name:** `inventory-updater-vm-new`
- **Zone:** `us-central1-a`
- **Project:** `boxwood-chassis-332307`
- **Status:** ✅ Running

## Deploy Files

SSH to the VM and run:

```bash
gcloud compute ssh inventory-updater-vm-new --zone=us-central1-a --project=boxwood-chassis-332307

# Once connected, deploy files:
curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-files | bash

# Set up cron job:
curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/setup-cron | bash

# Verify:
ls -lh /home/banzo/
crontab -l
```

## Files Deployed
- ✅ `vm_inventory_updater.py` (with February sheet support)
- ✅ `clover_creds.json`
- ✅ `service-account-key.json`

## Cron Job
Runs every 5 minutes:
```
*/5 * * * * cd /home/banzo && /usr/bin/python3 /home/banzo/vm_inventory_updater.py >> /home/banzo/inventory_cron.log 2>&1
```
