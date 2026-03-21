# PowerShell script to fix gcloud permissions and apply VM fix
# Run this script as Administrator

Write-Host "==================================================================================" -ForegroundColor Cyan
Write-Host "FIX GCLOUD PERMISSIONS AND APPLY VM FIX" -ForegroundColor Cyan
Write-Host "==================================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️  This script needs Administrator privileges to fix gcloud permissions" -ForegroundColor Yellow
    Write-Host "   Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Alternatively, you can manually:" -ForegroundColor Yellow
    Write-Host "1. Fix gcloud permissions:" -ForegroundColor Yellow
    Write-Host "   - Create directory: C:\Users\$env:USERNAME\AppData\Roaming\gcloud\logs" -ForegroundColor Yellow
    Write-Host "   - Give yourself full control to C:\Users\$env:USERNAME\AppData\Roaming\gcloud" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "2. Then run:" -ForegroundColor Yellow
    Write-Host "   gcloud compute scp apply_fix_on_vm.py inventory-updater-vm:/home/banzo/ --zone=us-central1-a" -ForegroundColor Yellow
    Write-Host "   gcloud compute ssh inventory-updater-vm --zone=us-central1-a" -ForegroundColor Yellow
    Write-Host "   python3 /home/banzo/apply_fix_on_vm.py" -ForegroundColor Yellow
    exit 1
}

Write-Host "[1] Fixing gcloud directory permissions..." -ForegroundColor Green

$gcloudDir = "$env:APPDATA\gcloud"
$logsDir = "$gcloudDir\logs"

# Create directories if they don't exist
if (-not (Test-Path $gcloudDir)) {
    New-Item -ItemType Directory -Path $gcloudDir -Force | Out-Null
    Write-Host "   Created: $gcloudDir" -ForegroundColor Gray
}

if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
    Write-Host "   Created: $logsDir" -ForegroundColor Gray
}

# Set permissions
try {
    $acl = Get-Acl $gcloudDir
    $permission = "$env:USERNAME","FullControl","ContainerInherit,ObjectInherit","None","Allow"
    $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule $permission
    $acl.SetAccessRule($accessRule)
    Set-Acl $gcloudDir $acl
    Write-Host "✅ Fixed permissions for: $gcloudDir" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Could not set permissions automatically: $_" -ForegroundColor Yellow
    Write-Host "   You may need to set permissions manually" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[2] Testing gcloud access..." -ForegroundColor Green

$gcloudTest = & gcloud --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ gcloud is working" -ForegroundColor Green
} else {
    Write-Host "❌ gcloud still has issues" -ForegroundColor Red
    Write-Host "   Output: $gcloudTest" -ForegroundColor Gray
}

Write-Host ""
Write-Host "[3] Applying VM fix..." -ForegroundColor Green
Write-Host ""

# Check if fix script exists
if (-not (Test-Path "apply_fix_on_vm.py")) {
    Write-Host "❌ apply_fix_on_vm.py not found in current directory" -ForegroundColor Red
    Write-Host "   Make sure you're in the project directory" -ForegroundColor Yellow
    exit 1
}

Write-Host "Copying fix script to VM..." -ForegroundColor Cyan
$copyResult = & gcloud compute scp apply_fix_on_vm.py inventory-updater-vm:/home/banzo/ --zone=us-central1-a 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Script copied to VM" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "Running fix script on VM..." -ForegroundColor Cyan
    $runResult = & gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && python3 apply_fix_on_vm.py" 2>&1
    
    Write-Host $runResult
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "==================================================================================" -ForegroundColor Green
        Write-Host "✅ VM FIX APPLIED SUCCESSFULLY!" -ForegroundColor Green
        Write-Host "==================================================================================" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "⚠️  Fix script ran but may have had issues" -ForegroundColor Yellow
        Write-Host "   Check the output above" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Failed to copy script to VM" -ForegroundColor Red
    Write-Host "   Error: $copyResult" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Manual steps:" -ForegroundColor Yellow
    Write-Host "1. gcloud compute scp apply_fix_on_vm.py inventory-updater-vm:/home/banzo/ --zone=us-central1-a" -ForegroundColor Yellow
    Write-Host "2. gcloud compute ssh inventory-updater-vm --zone=us-central1-a" -ForegroundColor Yellow
    Write-Host "3. python3 /home/banzo/apply_fix_on_vm.py" -ForegroundColor Yellow
}

Write-Host ""
