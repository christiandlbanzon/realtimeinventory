# SSH directly to VM using the IP we got from API
# This bypasses gcloud's credential issues

$vmIp = "34.69.171.53"
$username = "banzo"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "SSH DIRECT TO VM" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "VM IP: $vmIp" -ForegroundColor Yellow
Write-Host "Username: $username" -ForegroundColor Yellow
Write-Host ""

Write-Host "Attempting SSH connection..." -ForegroundColor Yellow
Write-Host ""

# Try SSH directly
try {
    # Use ssh command if available
    $sshCommand = "ssh $username@$vmIp 'cd /home/banzo && python3 apply_fix_on_vm.py'"
    Write-Host "Running: $sshCommand" -ForegroundColor Gray
    Write-Host ""
    
    Invoke-Expression $sshCommand
    
    Write-Host ""
    Write-Host "✅ Fix applied!" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "⚠️  Direct SSH failed. You may need to:" -ForegroundColor Yellow
    Write-Host "   1. Have SSH keys set up" -ForegroundColor White
    Write-Host "   2. Or use gcloud compute ssh (after fixing permissions)" -ForegroundColor White
    Write-Host ""
    Write-Host "MANUAL OPTION:" -ForegroundColor Cyan
    Write-Host "   ssh $username@$vmIp" -ForegroundColor White
    Write-Host "   Then run:" -ForegroundColor White
    Write-Host "     cd /home/banzo" -ForegroundColor Gray
    Write-Host "     python3 apply_fix_on_vm.py" -ForegroundColor Gray
}

Write-Host ""
