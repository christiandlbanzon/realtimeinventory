# PowerShell script to deploy files directly using gcloud compute scp
# No SSH needed - gcloud handles authentication

$VM_NAME = "real-time-inventory"
$ZONE = "us-central1-a"
$PROJECT_ID = "boxwood-chassis-332307"
$VM_USER = "banzo"
$VM_PATH = "/home/banzo"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DEPLOYING FILES DIRECTLY VIA GCLOUD" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "VM: $VM_NAME" -ForegroundColor Yellow
Write-Host "Zone: $ZONE" -ForegroundColor Yellow
Write-Host "Project: $PROJECT_ID" -ForegroundColor Yellow
Write-Host ""

# Files to deploy
$files = @(
    @{local="vm_inventory_updater_fixed.py"; remote="vm_inventory_updater.py"},
    @{local="clover_creds.json"; remote="clover_creds.json"},
    @{local="service-account-key.json"; remote="service-account-key.json"}
)

# Step 1: Copy files using gcloud compute scp
Write-Host "[1/2] Copying files to VM using gcloud compute scp..." -ForegroundColor Green
Write-Host ""

foreach ($file in $files) {
    $localFile = $file.local
    $remoteFile = "$VM_PATH/$($file.remote)"
    
    if (-not (Test-Path $localFile)) {
        Write-Host "❌ File not found: $localFile" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "  Copying $localFile -> $remoteFile..." -ForegroundColor Yellow
    
    try {
        gcloud compute scp $localFile "${VM_USER}@${VM_NAME}:${remoteFile}" `
            --zone=$ZONE `
            --project=$PROJECT_ID
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ $localFile copied successfully" -ForegroundColor Green
        } else {
            Write-Host "  ❌ Failed to copy $localFile" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "  ❌ Error copying $localFile : $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "[2/2] Setting up cron job..." -ForegroundColor Green
Write-Host ""

# Step 2: Set up cron using gcloud compute ssh --command
$cronCommand = "(crontab -l 2>/dev/null | grep -v 'vm_inventory_updater.py'; echo '*/5 * * * * cd $VM_PATH && /usr/bin/python3 $VM_PATH/vm_inventory_updater.py >> $VM_PATH/inventory_cron.log 2>&1') | crontab -"

try {
    gcloud compute ssh $VM_NAME `
        --zone=$ZONE `
        --project=$PROJECT_ID `
        --command=$cronCommand
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Cron job set up successfully" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Cron setup had issues, but files are deployed" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠️  Could not set up cron automatically: $_" -ForegroundColor Yellow
    Write-Host "  Files are deployed, but you may need to set up cron manually" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Files deployed:" -ForegroundColor Yellow
foreach ($file in $files) {
    Write-Host "  ✅ $($file.remote)" -ForegroundColor Green
}
Write-Host ""
Write-Host "To verify deployment:" -ForegroundColor Cyan
Write-Host "  gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT_ID" -ForegroundColor White
Write-Host "  ls -lh $VM_PATH/" -ForegroundColor White
Write-Host "  crontab -l" -ForegroundColor White
