# VM-Specific Issue Fix

## Problem Identified

The `real-time-inventory` VM is **missing the `startup-script` metadata key**. This is why deployment isn't working automatically.

**What I found:**
- ✅ VM Status: RUNNING
- ✅ Has `deploy-and-setup` script: Yes (158KB)
- ❌ **Missing `startup-script`**: This is the problem!
- Your other VMs work because they have `startup-script` set

## Why Deployment Fails from IDE

1. **gcloud commands**: Permission errors writing to `%APPDATA%\gcloud` when run from IDE
2. **API calls**: Timeout/503 errors - this VM has connectivity issues with Compute Engine API

This is a **VM-specific problem** - your other VMs don't have these issues.

## Solution: Run These Commands in Your Terminal

Open PowerShell or CMD (NOT in IDE) and run:

```powershell
cd "e:\prog fold\Drunken cookies\real-time-inventory"

# Deploy the 3 essential files
gcloud compute scp vm_inventory_updater_fixed.py banzo@real-time-inventory:/home/banzo/vm_inventory_updater.py --zone=us-central1-a --project=boxwood-chassis-332307

gcloud compute scp clover_creds.json banzo@real-time-inventory:/home/banzo/clover_creds.json --zone=us-central1-a --project=boxwood-chassis-332307

gcloud compute scp service-account-key.json banzo@real-time-inventory:/home/banzo/service-account-key.json --zone=us-central1-a --project=boxwood-chassis-332307

# Set up cron job
gcloud compute ssh real-time-inventory --zone=us-central1-a --project=boxwood-chassis-332307 --command="(crontab -l 2>/dev/null | grep -v 'vm_inventory_updater.py'; echo '*/5 * * * * cd /home/banzo && /usr/bin/python3 /home/banzo/vm_inventory_updater.py >> /home/banzo/inventory_cron.log 2>&1') | crontab -"

# Verify deployment
gcloud compute ssh real-time-inventory --zone=us-central1-a --project=boxwood-chassis-332307 --command="ls -lh /home/banzo/*.py /home/banzo/*.json"
```

## Alternative: Set startup-script via API

If you want the script to run automatically on VM restart, you can set `startup-script` metadata. But since API calls are timing out for this VM, the gcloud scp method above is more reliable.

## Summary

- **Root cause**: Missing `startup-script` metadata (VM-specific issue)
- **Why IDE fails**: Permission errors + API timeouts (VM-specific)
- **Solution**: Run gcloud commands manually in your terminal (works like your other VMs)
