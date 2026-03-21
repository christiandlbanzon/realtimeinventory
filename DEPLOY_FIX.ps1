# Deploy Biscoff Fix to VM
# Run this script in PowerShell with appropriate permissions

$ErrorActionPreference = "Stop"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "DEPLOY BISCOFF FIX TO VM" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

$VM_NAME = "inventory-updater-vm"
$ZONE = "us-central1-a"
$FIXED_FILE = "vm_inventory_updater_fixed.py"
$GCLOUD_PATH = "C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

# Check if file exists
if (-not (Test-Path $FIXED_FILE)) {
    Write-Host "ERROR: $FIXED_FILE not found!" -ForegroundColor Red
    exit 1
}

Write-Host "`n[1/2] Checking gcloud..." -ForegroundColor Yellow

# Check if gcloud exists
if (-not (Test-Path $GCLOUD_PATH)) {
    Write-Host "ERROR: gcloud not found at $GCLOUD_PATH" -ForegroundColor Red
    Write-Host "`nPlease install gcloud or run manually:" -ForegroundColor Yellow
    Write-Host "  gcloud compute scp $FIXED_FILE banzo@${VM_NAME}:/home/banzo/vm_inventory_updater.py --zone=$ZONE" -ForegroundColor White
    exit 1
}

Write-Host "  Found gcloud: $GCLOUD_PATH" -ForegroundColor Green

# Set service account
$env:GOOGLE_APPLICATION_CREDENTIALS = (Resolve-Path "service-account-key.json").Path
Write-Host "  Set GOOGLE_APPLICATION_CREDENTIALS" -ForegroundColor Green

Write-Host "`n[2/2] Deploying file to VM..." -ForegroundColor Yellow
Write-Host "  File: $FIXED_FILE" -ForegroundColor Gray
Write-Host "  Target: banzo@${VM_NAME}:/home/banzo/vm_inventory_updater.py" -ForegroundColor Gray
Write-Host "  Zone: $ZONE" -ForegroundColor Gray

try {
    & $GCLOUD_PATH compute scp $FIXED_FILE "banzo@${VM_NAME}:/home/banzo/vm_inventory_updater.py" --zone=$ZONE --quiet
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ SUCCESS! File deployed to VM" -ForegroundColor Green
        Write-Host "`nThe cron job will use the new code on the next run (every 5 minutes)." -ForegroundColor Cyan
        Write-Host "`nTo verify:" -ForegroundColor Yellow
        Write-Host "  gcloud compute ssh $VM_NAME --zone=$ZONE --command='grep -c \"\\*N\\* Cheesecake with Biscoff\" /home/banzo/vm_inventory_updater.py'" -ForegroundColor White
    } else {
        Write-Host "`n❌ Deployment failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
        Write-Host "`nTry running manually:" -ForegroundColor Yellow
        Write-Host "  gcloud compute scp $FIXED_FILE banzo@${VM_NAME}:/home/banzo/vm_inventory_updater.py --zone=$ZONE" -ForegroundColor White
        exit 1
    }
} catch {
    Write-Host "`n❌ Error: $_" -ForegroundColor Red
    Write-Host "`nTry running manually:" -ForegroundColor Yellow
    Write-Host "  gcloud compute scp $FIXED_FILE banzo@${VM_NAME}:/home/banzo/vm_inventory_updater.py --zone=$ZONE" -ForegroundColor White
    exit 1
}
