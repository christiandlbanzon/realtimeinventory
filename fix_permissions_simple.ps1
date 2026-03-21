# Simple script to fix gcloud permissions
# Run this FIRST as Administrator, then run the VM fix

Write-Host "Fixing gcloud directory permissions..." -ForegroundColor Cyan

$gcloudDir = "$env:APPDATA\gcloud"
$logsDir = "$gcloudDir\logs"

# Create directories
if (-not (Test-Path $gcloudDir)) {
    New-Item -ItemType Directory -Path $gcloudDir -Force | Out-Null
    Write-Host "Created: $gcloudDir" -ForegroundColor Green
}

if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
    Write-Host "Created: $logsDir" -ForegroundColor Green
}

# Try to set permissions (may fail if not admin)
try {
    $acl = Get-Acl $gcloudDir
    $permission = "$env:USERNAME","FullControl","ContainerInherit,ObjectInherit","None","Allow"
    $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule $permission
    $acl.SetAccessRule($accessRule)
    Set-Acl $gcloudDir $acl
    Write-Host "Permissions set successfully" -ForegroundColor Green
} catch {
    Write-Host "Could not set permissions automatically: $_" -ForegroundColor Yellow
    Write-Host "You may need to:" -ForegroundColor Yellow
    Write-Host "1. Right-click on: $gcloudDir" -ForegroundColor Yellow
    Write-Host "2. Properties -> Security -> Edit" -ForegroundColor Yellow
    Write-Host "3. Give your user Full Control" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Now try running:" -ForegroundColor Cyan
Write-Host "  gcloud compute scp apply_fix_on_vm.py inventory-updater-vm:/home/banzo/ --zone=us-central1-a" -ForegroundColor White
Write-Host "  gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command='cd /home/banzo && python3 apply_fix_on_vm.py'" -ForegroundColor White
