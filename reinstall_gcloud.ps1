# Reinstall gcloud to fix permission issues
# This will create a fresh installation with proper permissions

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "REINSTALLING GCLOUD CLI" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

$gcloudPath = "C:\Users\banzo\AppData\Local\Google\Cloud SDK"
$gcloudConfigPath = "$env:APPDATA\gcloud"

Write-Host "Current gcloud installation:" -ForegroundColor Yellow
Write-Host "  Path: $gcloudPath" -ForegroundColor Gray
Write-Host "  Config: $gcloudConfigPath" -ForegroundColor Gray
Write-Host ""

Write-Host "OPTION 1: Quick fix - just delete credentials.db and let gcloud recreate it" -ForegroundColor Cyan
Write-Host ""

$choice = Read-Host "Do you want to (1) Delete credentials.db only, or (2) Full reinstall? [1/2]"

if ($choice -eq "1") {
    Write-Host ""
    Write-Host "Deleting credentials.db..." -ForegroundColor Yellow
    
    $credentialsFile = "$gcloudConfigPath\credentials.db"
    if (Test-Path $credentialsFile) {
        try {
            Remove-Item $credentialsFile -Force
            Write-Host "✅ Deleted credentials.db" -ForegroundColor Green
            Write-Host ""
            Write-Host "gcloud will recreate it on next use with proper permissions." -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Now try:" -ForegroundColor Yellow
            Write-Host '  gcloud auth activate-service-account --key-file=service-account-key.json' -ForegroundColor White
            Write-Host '  gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && python3 apply_fix_on_vm.py"' -ForegroundColor White
        } catch {
            Write-Host "❌ Could not delete: $_" -ForegroundColor Red
            Write-Host "   You may need to delete it manually or run as Administrator" -ForegroundColor Yellow
        }
    } else {
        Write-Host "⚠️  credentials.db not found - it will be created on next gcloud use" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "OPTION 2: Full reinstall instructions" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Uninstall current gcloud:" -ForegroundColor Yellow
    Write-Host "   - Go to Settings > Apps > Google Cloud SDK > Uninstall" -ForegroundColor White
    Write-Host "   OR delete folder: $gcloudPath" -ForegroundColor White
    Write-Host ""
    Write-Host "2. Delete config (optional but recommended):" -ForegroundColor Yellow
    Write-Host "   - Delete folder: $gcloudConfigPath" -ForegroundColor White
    Write-Host ""
    Write-Host "3. Reinstall gcloud:" -ForegroundColor Yellow
    Write-Host "   - Download from: https://cloud.google.com/sdk/docs/install" -ForegroundColor White
    Write-Host "   - Run installer" -ForegroundColor White
    Write-Host ""
    Write-Host "4. Authenticate:" -ForegroundColor Yellow
    Write-Host '   gcloud auth activate-service-account --key-file=service-account-key.json' -ForegroundColor White
    Write-Host '   gcloud config set project boxwood-chassis-332307' -ForegroundColor White
}

Write-Host ""
