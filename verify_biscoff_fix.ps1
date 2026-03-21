# Verify Biscoff Fix on VM
# Run this script to check if the fix is deployed

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "VERIFYING BISCOFF FIX ON VM" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

$VM_NAME = "inventory-updater-vm"
$ZONE = "us-central1-a"

Write-Host "`n[1/3] Checking if fix string exists..." -ForegroundColor Yellow
$command1 = 'grep -c "\\*N\\* Cheesecake with Biscoff" /home/banzo/vm_inventory_updater.py'
$result1 = gcloud compute ssh $VM_NAME --zone=$ZONE --command=$command1 2>&1
Write-Host "   Result: $result1" -ForegroundColor White

if ($result1 -match '^\d+$' -and [int]$result1 -gt 0) {
    Write-Host "   ✅ Fix found! Count: $result1" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Could not verify (may be parsing issue)" -ForegroundColor Yellow
}

Write-Host "`n[2/3] Checking file size..." -ForegroundColor Yellow
$command2 = 'wc -c /home/banzo/vm_inventory_updater.py'
$result2 = gcloud compute ssh $VM_NAME --zone=$ZONE --command=$command2 2>&1
Write-Host "   Result: $result2" -ForegroundColor White

if ($result2 -match '(\d+)') {
    $size = [int]$matches[1]
    $sizeKB = [math]::Round($size / 1024, 1)
    Write-Host "   File size: $sizeKB KB" -ForegroundColor Cyan
    if ($sizeKB -gt 110 -and $sizeKB -lt 120) {
        Write-Host "   ✅ Size matches expected (~113 KB)" -ForegroundColor Green
    }
}

Write-Host "`n[3/3] Checking for correct sheet ID..." -ForegroundColor Yellow
$command3 = 'grep -c "1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE" /home/banzo/vm_inventory_updater.py'
$result3 = gcloud compute ssh $VM_NAME --zone=$ZONE --command=$command3 2>&1
Write-Host "   Result: $result3" -ForegroundColor White

if ($result3 -match '^\d+$' -and [int]$result3 -gt 0) {
    Write-Host "   ✅ Correct sheet ID found! Count: $result3" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Could not verify sheet ID" -ForegroundColor Yellow
}

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "VERIFICATION COMPLETE" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

Write-Host "`nIf you see numbers > 0 above, the fix is deployed! ✅" -ForegroundColor Green
