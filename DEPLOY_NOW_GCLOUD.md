# Deploy Real-Time Inventory Updater - gcloud CLI

**Stack:** gcloud CLI + Compute Engine  
**VM:** `real-time-inventory`  
**Zone:** `us-central1-a`  
**Project:** `boxwood-chassis-332307`

## Prerequisites

Make sure you're authenticated:
```powershell
gcloud auth login
gcloud config set project boxwood-chassis-332307
```

## Deploy Files

Run these commands from the project directory:

```powershell
cd "e:\prog fold\Drunken cookies\real-time-inventory"

# Deploy main script
gcloud compute scp vm_inventory_updater_fixed.py banzo@real-time-inventory:/home/banzo/vm_inventory_updater.py --zone=us-central1-a --project=boxwood-chassis-332307

# Deploy credentials
gcloud compute scp clover_creds.json banzo@real-time-inventory:/home/banzo/clover_creds.json --zone=us-central1-a --project=boxwood-chassis-332307

# Deploy service account key
gcloud compute scp service-account-key.json banzo@real-time-inventory:/home/banzo/service-account-key.json --zone=us-central1-a --project=boxwood-chassis-332307
```

## Set Up Cron Job

```powershell
gcloud compute ssh real-time-inventory --zone=us-central1-a --project=boxwood-chassis-332307 --command="(crontab -l 2>/dev/null | grep -v 'vm_inventory_updater.py'; echo '*/5 * * * * cd /home/banzo && /usr/bin/python3 /home/banzo/vm_inventory_updater.py >> /home/banzo/inventory_cron.log 2>&1') | crontab -"
```

## Verify Deployment

```powershell
# Check files exist
gcloud compute ssh real-time-inventory --zone=us-central1-a --project=boxwood-chassis-332307 --command="ls -lh /home/banzo/*.py /home/banzo/*.json"

# Check cron job
gcloud compute ssh real-time-inventory --zone=us-central1-a --project=boxwood-chassis-332307 --command="crontab -l"

# Check logs (after first run)
gcloud compute ssh real-time-inventory --zone=us-central1-a --project=boxwood-chassis-332307 --command="tail -50 /home/banzo/inventory_cron.log"
```

## All-in-One Script

Save this as `deploy.ps1` and run it from a **regular PowerShell terminal** (not IDE):

```powershell
$VM_NAME = "real-time-inventory"
$ZONE = "us-central1-a"
$PROJECT = "boxwood-chassis-332307"

cd "e:\prog fold\Drunken cookies\real-time-inventory"

Write-Host "Deploying files..." -ForegroundColor Cyan
gcloud compute scp vm_inventory_updater_fixed.py banzo@$VM_NAME:/home/banzo/vm_inventory_updater.py --zone=$ZONE --project=$PROJECT
gcloud compute scp clover_creds.json banzo@$VM_NAME:/home/banzo/clover_creds.json --zone=$ZONE --project=$PROJECT
gcloud compute scp service-account-key.json banzo@$VM_NAME:/home/banzo/service-account-key.json --zone=$ZONE --project=$PROJECT

Write-Host "Setting up cron..." -ForegroundColor Cyan
gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT --command="(crontab -l 2>/dev/null | grep -v 'vm_inventory_updater.py'; echo '*/5 * * * * cd /home/banzo && /usr/bin/python3 /home/banzo/vm_inventory_updater.py >> /home/banzo/inventory_cron.log 2>&1') | crontab -"

Write-Host "Deployment complete!" -ForegroundColor Green
```

## Note

**Why run from regular terminal?**  
The IDE has permission restrictions that prevent gcloud from writing to `%APPDATA%\gcloud`. Running from a regular PowerShell/CMD window avoids this issue. This is the same method you use for your other working VMs.
