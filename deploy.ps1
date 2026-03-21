# Deploy Real-Time Inventory Updater using gcloud CLI
# Run this from a regular PowerShell terminal (not IDE) to avoid permission issues

$VM_NAME = "real-time-inventory"
$ZONE = "us-central1-a"
$PROJECT = "boxwood-chassis-332307"

cd "e:\prog fold\Drunken cookies\real-time-inventory"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "DEPLOYING TO VM: $VM_NAME" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

# Deploy files
Write-Host "`n[1/3] Deploying files via gcloud compute scp..." -ForegroundColor Yellow

Write-Host "  Uploading vm_inventory_updater_fixed.py..." -ForegroundColor Gray
gcloud compute scp vm_inventory_updater_fixed.py "banzo@${VM_NAME}:/home/banzo/vm_inventory_updater.py" --zone=$ZONE --project=$PROJECT
if ($LASTEXITCODE -ne 0) { Write-Host "  FAILED" -ForegroundColor Red; exit 1 }
Write-Host "  OK" -ForegroundColor Green

Write-Host "  Uploading clover_creds.json..." -ForegroundColor Gray
gcloud compute scp clover_creds.json "banzo@${VM_NAME}:/home/banzo/clover_creds.json" --zone=$ZONE --project=$PROJECT
if ($LASTEXITCODE -ne 0) { Write-Host "  FAILED" -ForegroundColor Red; exit 1 }
Write-Host "  OK" -ForegroundColor Green

Write-Host "  Uploading service-account-key.json..." -ForegroundColor Gray
gcloud compute scp service-account-key.json "banzo@${VM_NAME}:/home/banzo/service-account-key.json" --zone=$ZONE --project=$PROJECT
if ($LASTEXITCODE -ne 0) { Write-Host "  FAILED" -ForegroundColor Red; exit 1 }
Write-Host "  OK" -ForegroundColor Green

# Set up cron
Write-Host "`n[2/3] Setting up cron job..." -ForegroundColor Yellow
$cronCmd = "(crontab -l 2>/dev/null | grep -v 'vm_inventory_updater.py'; echo '*/5 * * * * cd /home/banzo && /usr/bin/python3 /home/banzo/vm_inventory_updater.py >> /home/banzo/inventory_cron.log 2>&1') | crontab -"
gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT --command=$cronCmd
if ($LASTEXITCODE -ne 0) { Write-Host "  WARNING: Cron setup had issues" -ForegroundColor Yellow }
Write-Host "  OK" -ForegroundColor Green

# Verify
Write-Host "`n[3/3] Verifying deployment..." -ForegroundColor Yellow
gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT --command="ls -lh /home/banzo/*.py /home/banzo/*.json"
Write-Host "  OK" -ForegroundColor Green

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "DEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "`nVM: $VM_NAME" -ForegroundColor White
Write-Host "Cron: Every 5 minutes" -ForegroundColor White
Write-Host "`nCheck logs: gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT --command=`"tail -50 /home/banzo/inventory_cron.log`"" -ForegroundColor Gray
