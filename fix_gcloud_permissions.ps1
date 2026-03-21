# Fix gcloud directory permissions
# Run this script to fix the permission issues

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "FIXING GCLOUD PERMISSIONS" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

$gcloudDir = "$env:APPDATA\gcloud"
$logsDir = "$gcloudDir\logs"
$configDir = "$gcloudDir\configurations"

Write-Host "Checking directories..." -ForegroundColor Yellow

# Create directories if they don't exist
if (-not (Test-Path $gcloudDir)) {
    New-Item -ItemType Directory -Path $gcloudDir -Force | Out-Null
    Write-Host "✅ Created: $gcloudDir" -ForegroundColor Green
} else {
    Write-Host "✅ Exists: $gcloudDir" -ForegroundColor Green
}

if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
    Write-Host "✅ Created: $logsDir" -ForegroundColor Green
} else {
    Write-Host "✅ Exists: $logsDir" -ForegroundColor Green
}

if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
    Write-Host "✅ Created: $configDir" -ForegroundColor Green
} else {
    Write-Host "✅ Exists: $configDir" -ForegroundColor Green
}

Write-Host ""
Write-Host "Setting permissions..." -ForegroundColor Yellow

try {
    # Get current ACL
    $acl = Get-Acl $gcloudDir
    
    # Get current user
    $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    
    # Create access rule for current user with full control
    $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $currentUser,
        "FullControl",
        "ContainerInherit,ObjectInherit",
        "None",
        "Allow"
    )
    
    # Add the rule
    $acl.SetAccessRule($accessRule)
    
    # Apply to directory
    Set-Acl $gcloudDir $acl
    
    Write-Host "✅ Permissions set for: $gcloudDir" -ForegroundColor Green
    
    # Also set for logs directory
    if (Test-Path $logsDir) {
        $logsAcl = Get-Acl $logsDir
        $logsAcl.SetAccessRule($accessRule)
        Set-Acl $logsDir $logsAcl
        Write-Host "✅ Permissions set for: $logsDir" -ForegroundColor Green
    }
    
    # Also set for configurations directory
    if (Test-Path $configDir) {
        $configAcl = Get-Acl $configDir
        $configAcl.SetAccessRule($accessRule)
        Set-Acl $configDir $configAcl
        Write-Host "✅ Permissions set for: $configDir" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host "✅ PERMISSIONS FIXED!" -ForegroundColor Green
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Now try running the VM fix:" -ForegroundColor Cyan
    Write-Host '  gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && python3 apply_fix_on_vm.py"' -ForegroundColor White
    
} catch {
    Write-Host ""
    Write-Host "⚠️  Could not set permissions automatically: $_" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please set permissions manually:" -ForegroundColor Yellow
    Write-Host "1. Open File Explorer" -ForegroundColor White
    Write-Host "2. Go to: $gcloudDir" -ForegroundColor White
    Write-Host "3. Right-click → Properties → Security → Edit" -ForegroundColor White
    Write-Host "4. Select your user → Check 'Full Control' → Apply" -ForegroundColor White
    Write-Host "5. Check 'Replace all child object permissions'" -ForegroundColor White
}

Write-Host ""
