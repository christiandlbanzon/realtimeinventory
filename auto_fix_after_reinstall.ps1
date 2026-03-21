# Automated fix after gcloud reinstall
# Run this AFTER you've reinstalled gcloud

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "AUTOMATED VM FIX - Post Reinstall" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

$projectDir = "e:\prog fold\Drunken cookies\real-time-inventory"
Set-Location $projectDir

Write-Host "Step 1: Authenticating with service account..." -ForegroundColor Yellow
try {
    $result = & gcloud auth activate-service-account --key-file=service-account-key.json 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Authentication successful!" -ForegroundColor Green
    } else {
        Write-Host "❌ Authentication failed:" -ForegroundColor Red
        Write-Host $result
        exit 1
    }
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 2: Setting project..." -ForegroundColor Yellow
try {
    $result = & gcloud config set project boxwood-chassis-332307 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Project set!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Warning: $result" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Warning: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 3: Applying fix on VM..." -ForegroundColor Yellow
Write-Host ""

$vmName = "inventory-updater-vm"
$zone = "us-central1-a"
$command = "cd /home/banzo && python3 apply_fix_on_vm.py"

Write-Host "Executing: gcloud compute ssh $vmName --zone=$zone --command=`"$command`"" -ForegroundColor Gray
Write-Host ""

try {
    & gcloud compute ssh $vmName --zone=$zone --command=$command
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "================================================================================" -ForegroundColor Green
        Write-Host "✅ FIX APPLIED SUCCESSFULLY!" -ForegroundColor Green
        Write-Host "================================================================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "The promotion quantity fix is now active on the VM." -ForegroundColor Cyan
        Write-Host "Future updates will correctly count items like 'Cheesecake with Biscoff'." -ForegroundColor Cyan
    } else {
        Write-Host ""
        Write-Host "❌ SSH command failed. Exit code: $LASTEXITCODE" -ForegroundColor Red
        Write-Host ""
        Write-Host "Try manually:" -ForegroundColor Yellow
        Write-Host "  gcloud compute ssh $vmName --zone=$zone" -ForegroundColor White
        Write-Host "  Then run: cd /home/banzo && python3 apply_fix_on_vm.py" -ForegroundColor White
    }
} catch {
    Write-Host ""
    Write-Host "❌ Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Try manually:" -ForegroundColor Yellow
    Write-Host "  gcloud compute ssh $vmName --zone=$zone" -ForegroundColor White
    Write-Host "  Then run: cd /home/banzo && python3 apply_fix_on_vm.py" -ForegroundColor White
}

Write-Host ""
