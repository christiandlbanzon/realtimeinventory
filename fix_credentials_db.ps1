# Fix credentials.db file permissions specifically
# This file is blocking gcloud from working

$credentialsFile = "$env:APPDATA\gcloud\credentials.db"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "FIXING CREDENTIALS.DB FILE PERMISSIONS" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $credentialsFile) {
    Write-Host "Found credentials.db file" -ForegroundColor Green
    Write-Host "Location: $credentialsFile" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "Setting permissions..." -ForegroundColor Yellow
    
    try {
        $acl = Get-Acl $credentialsFile
        $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
        $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $currentUser,
            "FullControl",
            "Allow"
        )
        $acl.SetAccessRule($accessRule)
        Set-Acl $credentialsFile $acl
        
        Write-Host "✅ Permissions set for credentials.db" -ForegroundColor Green
        Write-Host ""
        Write-Host "Now try running:" -ForegroundColor Cyan
        Write-Host '  gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && python3 apply_fix_on_vm.py"' -ForegroundColor White
        
    } catch {
        Write-Host "⚠️  Could not set permissions automatically: $_" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Please fix manually:" -ForegroundColor Yellow
        Write-Host "1. Go to: $credentialsFile" -ForegroundColor White
        Write-Host "2. Right-click → Properties → Security → Edit" -ForegroundColor White
        Write-Host "3. Select your user → Check 'Full Control' → Apply" -ForegroundColor White
    }
} else {
    Write-Host "⚠️  credentials.db file not found" -ForegroundColor Yellow
    Write-Host "   It will be created when gcloud runs" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Make sure the gcloud folder has write permissions:" -ForegroundColor Yellow
    Write-Host "   $env:APPDATA\gcloud" -ForegroundColor White
}

Write-Host ""
