# Check gcloud status and help with reinstall if needed

function Show-ReinstallInstructions {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Yellow
    Write-Host "REINSTALL INSTRUCTIONS" -ForegroundColor Yellow
    Write-Host "================================================================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. UNINSTALL:" -ForegroundColor Cyan
    Write-Host "   Settings → Apps → Google Cloud SDK → Uninstall" -ForegroundColor White
    Write-Host ""
    Write-Host "2. DELETE CONFIG:" -ForegroundColor Cyan
    Write-Host "   Delete folder: C:\Users\banzo\AppData\Roaming\gcloud" -ForegroundColor White
    Write-Host ""
    Write-Host "3. REINSTALL:" -ForegroundColor Cyan
    Write-Host "   Download: https://cloud.google.com/sdk/docs/install" -ForegroundColor White
    Write-Host "   Run installer" -ForegroundColor White
    Write-Host ""
    Write-Host "4. RUN FIX SCRIPT:" -ForegroundColor Cyan
    Write-Host "   .\auto_fix_after_reinstall.ps1" -ForegroundColor White
    Write-Host ""
}

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "GCLOUD STATUS CHECK" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if gcloud is installed
Write-Host "Checking gcloud installation..." -ForegroundColor Yellow
try {
    $version = & gcloud --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ gcloud is installed" -ForegroundColor Green
        Write-Host $version
        Write-Host ""
        
        # Check if it works
        Write-Host "Testing gcloud functionality..." -ForegroundColor Yellow
        try {
            $test = & gcloud config list 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ gcloud appears to be working!" -ForegroundColor Green
                Write-Host ""
                Write-Host "You can try running the fix now:" -ForegroundColor Cyan
                Write-Host "  .\auto_fix_after_reinstall.ps1" -ForegroundColor White
            } else {
                Write-Host "⚠️  gcloud has issues. Reinstall recommended." -ForegroundColor Yellow
                Show-ReinstallInstructions
            }
        } catch {
            Write-Host "⚠️  gcloud has issues. Reinstall recommended." -ForegroundColor Yellow
            Show-ReinstallInstructions
        }
    } else {
        Write-Host "❌ gcloud not found or not working" -ForegroundColor Red
        Show-ReinstallInstructions
    }
} catch {
    Write-Host "❌ gcloud not found" -ForegroundColor Red
    Show-ReinstallInstructions
}

Write-Host ""
