# 🚀 Deploy Now - Simple Instructions

## Quick Deploy (Choose One)

### Option 1: PowerShell Script (Recommended)
```powershell
.\run_deployment.ps1
```

### Option 2: Batch File
```cmd
run_deployment.bat
```

### Option 3: Manual Command
Run this in your terminal:
```bash
gcloud compute ssh real-time-inventory --zone=us-central1-a --project=boxwood-chassis-332307 --command="curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-and-setup | bash"
```

## What This Does

✅ Deploys 3 essential files to `/home/banzo/`:
- `vm_inventory_updater.py` (with February sheet support)
- `clover_creds.json`
- `service-account-key.json`

✅ Sets up cron job (runs every 5 minutes)

✅ Shows verification output

## Verify Deployment

After running, SSH to the VM:
```bash
gcloud compute ssh real-time-inventory --zone=us-central1-a --project=boxwood-chassis-332307
```

Then check:
```bash
ls -lh /home/banzo/
crontab -l
```

## Current Status

- ✅ VM is running: `real-time-inventory`
- ✅ Deployment script is ready in VM metadata
- ✅ Files are ready locally
- ⏳ Just needs to be executed (run the script above!)
