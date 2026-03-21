# Quick VM Fix - Try SSH approach
# This script attempts to SSH and run the fix

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "QUICK VM FIX - Attempting SSH" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

$vmName = "inventory-updater-vm"
$zone = "us-central1-a"

Write-Host "Attempting to SSH to VM..." -ForegroundColor Yellow
Write-Host ""

# Try SSH with command execution
$command = "cd /home/banzo && python3 apply_fix_on_vm.py"
$sshCommand = "gcloud compute ssh $vmName --zone=$zone --command=`"$command`""

Write-Host "Running: $sshCommand" -ForegroundColor Gray
Write-Host ""

try {
    Invoke-Expression $sshCommand
    Write-Host ""
    Write-Host "✅ Fix applied successfully!" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "❌ SSH command failed. Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "MANUAL OPTION:" -ForegroundColor Yellow
    Write-Host "1. Open a NEW PowerShell window (fresh session)" -ForegroundColor White
    Write-Host "2. Run: gcloud compute ssh $vmName --zone=$zone" -ForegroundColor White
    Write-Host "3. Once connected, run:" -ForegroundColor White
    Write-Host "   cd /home/banzo" -ForegroundColor Gray
    Write-Host "   python3 apply_fix_on_vm.py" -ForegroundColor Gray
}

Write-Host ""
