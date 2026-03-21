# PowerShell script to run VM fix
# Right-click and "Run with PowerShell" or run from PowerShell

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "RUNNING VM FIX" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location "e:\prog fold\Drunken cookies\real-time-inventory"

Write-Host "Executing fix script on VM..." -ForegroundColor Yellow
$result = & gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && python3 apply_fix_on_vm.py" 2>&1

Write-Host $result

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host "VERIFYING FIX" -ForegroundColor Green
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host ""
    
    & gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="grep -A 5 'FIX FOR PROMOTION ITEMS' /home/banzo/vm_inventory_updater.py"
    
    Write-Host ""
    Write-Host "✅ Fix applied successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "⚠️  Command had issues. Try running manually:" -ForegroundColor Yellow
    Write-Host "   gcloud compute ssh inventory-updater-vm --zone=us-central1-a" -ForegroundColor White
    Write-Host "   cd /home/banzo" -ForegroundColor White
    Write-Host "   python3 apply_fix_on_vm.py" -ForegroundColor White
}

Write-Host ""
Read-Host "Press Enter to exit"
