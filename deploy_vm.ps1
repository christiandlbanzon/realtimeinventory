# Deploy Real-Time Inventory Updater to GCP VM
# Run this script as Administrator or ensure gcloud has write permissions

Write-Host "=================================================================================" -ForegroundColor Cyan
Write-Host "Deploying Real-Time Inventory Updater to GCP VM: real-time-inventory" -ForegroundColor Cyan
Write-Host "=================================================================================" -ForegroundColor Cyan
Write-Host ""

$GCLOUD_PATH = "C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$PROJECT_ID = "boxwood-chassis-332307"
$VM_NAME = "real-time-inventory"
$ZONE = "us-central1-a"
$USERNAME = "banzo"

# Check if gcloud exists
if (-not (Test-Path $GCLOUD_PATH)) {
    Write-Host "ERROR: gcloud not found at $GCLOUD_PATH" -ForegroundColor Red
    exit 1
}

# Step 1: Authenticate
Write-Host "Step 1: Checking authentication..." -ForegroundColor Yellow
& $GCLOUD_PATH auth list
if ($LASTEXITCODE -ne 0) {
    Write-Host "Please authenticate first. Opening browser..." -ForegroundColor Yellow
    & $GCLOUD_PATH auth login
}

# Step 2: Set project
Write-Host "`nStep 2: Setting project..." -ForegroundColor Yellow
& $GCLOUD_PATH config set project $PROJECT_ID

# Step 3: Check if VM exists
Write-Host "`nStep 3: Checking if VM exists..." -ForegroundColor Yellow
$vmExists = & $GCLOUD_PATH compute instances list --filter "name=$VM_NAME" --format="value(name)" 2>$null
if ($vmExists -eq $VM_NAME) {
    Write-Host "VM '$VM_NAME' already exists. Continuing with deployment..." -ForegroundColor Green
} else {
    Write-Host "Creating new VM '$VM_NAME'..." -ForegroundColor Yellow
    & $GCLOUD_PATH compute instances create $VM_NAME `
        --zone=$ZONE `
        --machine-type=e2-micro `
        --image-family=ubuntu-2204-lts `
        --image-project=ubuntu-os-cloud `
        --boot-disk-size=20GB `
        --boot-disk-type=pd-standard
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create VM" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Waiting for VM to be ready (30 seconds)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
}

# Step 4: Upload files
Write-Host "`nStep 4: Uploading files..." -ForegroundColor Yellow
$files = @(
    "vm_inventory_updater_fixed.py",
    "service-account-key.json",
    "clover_creds.json",
    "requirements.txt"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "Uploading $file..." -ForegroundColor Cyan
        & $GCLOUD_PATH compute scp $file "${USERNAME}@${VM_NAME}:~/" --zone=$ZONE
        if ($LASTEXITCODE -ne 0) {
            Write-Host "WARNING: Failed to upload $file" -ForegroundColor Yellow
        }
    } else {
        Write-Host "ERROR: File not found: $file" -ForegroundColor Red
        exit 1
    }
}

# Rename main file on VM
Write-Host "`nRenaming main file on VM..." -ForegroundColor Yellow
& $GCLOUD_PATH compute ssh "${USERNAME}@${VM_NAME}" --zone=$ZONE --command="mv ~/vm_inventory_updater_fixed.py ~/vm_inventory_updater.py" 2>$null

# Step 5: Setup environment
Write-Host "`nStep 5: Setting up VM environment..." -ForegroundColor Yellow
$setupCommands = @(
    "sudo apt-get update",
    "sudo apt-get install -y python3 python3-pip python3-venv python3-dev build-essential",
    "python3 -m venv ~/venv",
    "~/venv/bin/pip install --upgrade pip",
    "~/venv/bin/pip install -r ~/requirements.txt",
    "chmod +x ~/vm_inventory_updater.py",
    "mkdir -p ~/logs"
)

foreach ($cmd in $setupCommands) {
    Write-Host "Running: $cmd" -ForegroundColor Gray
    & $GCLOUD_PATH compute ssh "${USERNAME}@${VM_NAME}" --zone=$ZONE --command=$cmd 2>&1 | Out-Null
}

# Step 6: Setup cron
Write-Host "`nStep 6: Setting up cron job..." -ForegroundColor Yellow
$sheetId = "1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno"
$cronCmd = "cd ~ && export INVENTORY_SHEET_ID=$sheetId && ~/venv/bin/python ~/vm_inventory_updater.py >> ~/inventory_cron.log 2>&1"
$cronEntry = "*/5 * * * * $cronCmd"

# Create temp cron file
$tempCron = "temp_cron.txt"
$cronEntry | Out-File -FilePath $tempCron -Encoding utf8

# Upload and install cron
& $GCLOUD_PATH compute scp $tempCron "${USERNAME}@${VM_NAME}:~/temp_cron.txt" --zone=$ZONE
& $GCLOUD_PATH compute ssh "${USERNAME}@${VM_NAME}" --zone=$ZONE --command="crontab ~/temp_cron.txt && rm ~/temp_cron.txt"
Remove-Item $tempCron -ErrorAction SilentlyContinue

Write-Host "`n=================================================================================" -ForegroundColor Green
Write-Host "DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "=================================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "VM: $VM_NAME" -ForegroundColor Cyan
Write-Host "Zone: $ZONE" -ForegroundColor Cyan
Write-Host "Cron: Runs every 5 minutes" -ForegroundColor Cyan
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  SSH: gcloud compute ssh ${USERNAME}@${VM_NAME} --zone=$ZONE"
Write-Host "  Logs: gcloud compute ssh ${USERNAME}@${VM_NAME} --zone=$ZONE --command='tail -50 ~/inventory_cron.log'"
Write-Host "  Test: gcloud compute ssh ${USERNAME}@${VM_NAME} --zone=$ZONE --command='cd ~ && ~/venv/bin/python ~/vm_inventory_updater.py'"
