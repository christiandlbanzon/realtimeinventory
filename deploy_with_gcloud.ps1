# Deploy Real-Time Inventory Updater to VM using gcloud CLI
# This matches your deployment stack: gcloud CLI + Compute Engine

$ErrorActionPreference = "Stop"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "DEPLOYING TO VM VIA GCLOUD CLI" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

$VM_NAME = "real-time-inventory"
$ZONE = "us-central1-a"
$PROJECT = "boxwood-chassis-332307"
$VM_USER = "banzo"

# Files to deploy
$files = @(
    @{Local="vm_inventory_updater_fixed.py"; Remote="/home/banzo/vm_inventory_updater.py"},
    @{Local="clover_creds.json"; Remote="/home/banzo/clover_creds.json"},
    @{Local="service-account-key.json"; Remote="/home/banzo/service-account-key.json"}
)

# Check if files exist
Write-Host "`n[1/4] Checking files..." -ForegroundColor Yellow
foreach ($file in $files) {
    if (-not (Test-Path $file.Local)) {
        Write-Host "ERROR: File not found: $($file.Local)" -ForegroundColor Red
        exit 1
    }
    Write-Host "  OK: $($file.Local)" -ForegroundColor Green
}

# Deploy files
Write-Host "`n[2/4] Deploying files via gcloud compute scp..." -ForegroundColor Yellow
foreach ($file in $files) {
    Write-Host "  Uploading $($file.Local)..." -ForegroundColor Cyan
    
    $scpCmd = "gcloud compute scp $($file.Local) ${VM_USER}@${VM_NAME}:$($file.Remote) --zone=$ZONE --project=$PROJECT"
    
    try {
        Invoke-Expression $scpCmd
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    OK: $($file.Local) deployed" -ForegroundColor Green
        } else {
            Write-Host "    FAILED: Exit code $LASTEXITCODE" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "    ERROR: $_" -ForegroundColor Red
        exit 1
    }
}

# Set up cron job
Write-Host "`n[3/4] Setting up cron job via gcloud compute ssh..." -ForegroundColor Yellow
$cronCmd = "(crontab -l 2>/dev/null | grep -v 'vm_inventory_updater.py'; echo '*/5 * * * * cd /home/banzo && /usr/bin/python3 /home/banzo/vm_inventory_updater.py >> /home/banzo/inventory_cron.log 2>&1') | crontab -"
$sshCmd = "gcloud compute ssh ${VM_NAME} --zone=$ZONE --project=$PROJECT --command=`"$cronCmd`""

try {
    Write-Host "  Setting cron..." -ForegroundColor Cyan
    Invoke-Expression $sshCmd
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    OK: Cron job set" -ForegroundColor Green
    } else {
        Write-Host "    WARNING: Cron setup may have issues (exit code $LASTEXITCODE)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "    ERROR: $_" -ForegroundColor Red
    exit 1
}

# Verify deployment
Write-Host "`n[4/4] Verifying deployment..." -ForegroundColor Yellow
$verifyCmd = "gcloud compute ssh ${VM_NAME} --zone=$ZONE --project=$PROJECT --command=`"ls -lh /home/banzo/*.py /home/banzo/*.json`""

try {
    Write-Host "  Checking files on VM..." -ForegroundColor Cyan
    Invoke-Expression $verifyCmd
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    OK: Files verified" -ForegroundColor Green
    }
} catch {
    Write-Host "    WARNING: Verification had issues" -ForegroundColor Yellow
}

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "DEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "`nVM: $VM_NAME" -ForegroundColor White
Write-Host "Files deployed: 3" -ForegroundColor White
Write-Host "Cron job: Every 5 minutes" -ForegroundColor White
Write-Host "`nTo check logs:" -ForegroundColor Yellow
Write-Host "  gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT --command=`"tail -50 /home/banzo/inventory_cron.log`"" -ForegroundColor Gray
