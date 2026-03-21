# PowerShell script to deploy files using gcloud CLI
# Run this from your terminal (not IDE) after gcloud auth login

$VM_NAME = "real-time-inventory"
$ZONE = "us-central1-a"
$PROJECT_ID = "boxwood-chassis-332307"
$VM_USER = "banzo"
$VM_PATH = "/home/banzo"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DEPLOYING TO VM VIA GCLOUD CLI" -ForegroundColor Cyan
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

# Step 1: Copy files
Write-Host "[1/2] Copying files to VM..." -ForegroundColor Green
Write-Host ""

foreach ($file in $files) {
    $localFile = $file.local
    $remoteFile = "$VM_PATH/$($file.remote)"
    
    if (-not (Test-Path $localFile)) {
        Write-Host "❌ File not found: $localFile" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "  Copying $localFile -> $remoteFile..." -ForegroundColor Yellow
    
    gcloud compute scp $localFile "${VM_USER}@${VM_NAME}:${remoteFile}" `
        --zone=$ZONE `
        --project=$PROJECT_ID
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ $localFile copied successfully" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Failed to copy $localFile" -ForegroundColor Red
        exit 1
    }
}

# Step 2: Set up cron
Write-Host ""
Write-Host "[2/2] Setting up cron job..." -ForegroundColor Green
Write-Host ""

$cronCommand = "(crontab -l 2>/dev/null | grep -v 'vm_inventory_updater.py'; echo '*/5 * * * * cd $VM_PATH && /usr/bin/python3 $VM_PATH/vm_inventory_updater.py >> $VM_PATH/inventory_cron.log 2>&1') | crontab -"

gcloud compute ssh $VM_NAME `
    --zone=$ZONE `
    --project=$PROJECT_ID `
    --command=$cronCommand

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Cron job set up successfully" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Cron setup had issues, but files are deployed" -ForegroundColor Yellow
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
Write-Host "⚠️  IMPORTANT: Share February sheet with Editor access:" -ForegroundColor Yellow
Write-Host "   Sheet ID: 1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4" -ForegroundColor White
Write-Host "   Service Account: 703996360436-compute@developer.gserviceaccount.com" -ForegroundColor White
Write-Host "   Permission: Editor" -ForegroundColor White
Write-Host ""
Write-Host "To verify deployment:" -ForegroundColor Cyan
Write-Host "  gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT_ID" -ForegroundColor White
Write-Host "  ls -lh $VM_PATH/" -ForegroundColor White
Write-Host "  crontab -l" -ForegroundColor White
