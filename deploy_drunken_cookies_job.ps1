# Deploy NEW Cloud Run Job specifically for Drunken Cookies sheet updates
# This is SEPARATE from inventory-updater

$ErrorActionPreference = "Stop"
$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""

$PROJECT_ID = "boxwood-chassis-332307"
$REGION = "us-east1"
$JOB_NAME = "drunken-cookies-daily"
$SCHEDULER_NAME = "${JOB_NAME}-schedule"
$SERVICE_ACCOUNT = "703996360436-compute@developer.gserviceaccount.com"
$IMAGE = "gcr.io/${PROJECT_ID}/${JOB_NAME}"

# Daily schedule: 5 AM UTC = 1 AM Puerto Rico (end-of-day run processes yesterday)
$DAILY_CRON = "0 5 * * *"

Write-Host "=================================================================================="
Write-Host "DEPLOY NEW CLOUD RUN JOB - DRUNKEN COOKIES ONLY"
Write-Host "=================================================================================="
Write-Host "Project: $PROJECT_ID"
Write-Host "Job: $JOB_NAME (NEW - separate from inventory-updater)"
Write-Host "Schedule: Daily at 1 AM Puerto Rico (5 AM UTC)"
Write-Host "Purpose: Updates ONLY Drunken Cookies sheet"
Write-Host ""

# Find gcloud
$gcloud = Get-Command gcloud -ErrorAction SilentlyContinue
if ($gcloud) {
    $gcloud = $gcloud.Source
} else {
    $gcloudPaths = @(
        "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.ps1"
    )
    
    foreach ($path in $gcloudPaths) {
        if (Test-Path $path) {
            try {
                $result = & $path --version 2>&1
                if ($LASTEXITCODE -eq 0) {
                    $gcloud = $path
                    break
                }
            } catch {
                continue
            }
        }
    }
}

if (-not $gcloud) {
    Write-Host "ERROR: gcloud CLI not found"
    exit 1
}

Write-Host "Using gcloud: $gcloud"
Write-Host ""

# Check required files
Write-Host "[1/4] Checking required files..."
$requiredFiles = @(
    "drunken_cookies_daily.py",
    "vm_inventory_updater_fixed.py",
    "clover_creds.json",
    "service-account-key.json"
)

foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Host "ERROR: Required file not found: $file"
        exit 1
    }
    Write-Host "  OK: $file"
}

# Create Dockerfile for Drunken Cookies job
Write-Host ""
Write-Host "[2/4] Creating Dockerfile for Drunken Cookies job..."
$dockerfile = @"
FROM python:3.12-slim

WORKDIR /app

# Copy credentials
COPY clover_creds.json .
COPY service-account-key.json .

# Copy scripts
COPY vm_inventory_updater_fixed.py .
COPY drunken_cookies_daily.py .

# Install dependencies
RUN pip install --no-cache-dir \
    google-auth \
    google-auth-oauthlib \
    google-auth-httplib2 \
    google-api-python-client \
    requests \
    python-dotenv \
    fuzzywuzzy \
    python-Levenshtein

# Set environment variable for service account
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json

# Run the Drunken Cookies updater
CMD ["python", "drunken_cookies_daily.py"]
"@

# Backup existing Dockerfile if it exists
if (Test-Path "Dockerfile") {
    Copy-Item "Dockerfile" "Dockerfile.backup"
}

$dockerfile | Out-File -FilePath "Dockerfile" -Encoding utf8
Write-Host "  OK: Dockerfile created"

# Build Docker image
Write-Host ""
Write-Host "[3/4] Building Docker image..."
& $gcloud builds submit --tag $IMAGE --project $PROJECT_ID

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker build failed"
    exit 1
}
Write-Host "  OK: Image built"

# Create Cloud Run Job
Write-Host ""
Write-Host "[4/4] Creating Cloud Run Job..."
$jobExists = & $gcloud run jobs describe $JOB_NAME --region $REGION --project $PROJECT_ID 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Job exists, updating..."
    & $gcloud run jobs update $JOB_NAME `
        --image $IMAGE `
        --region $REGION `
        --project $PROJECT_ID `
        --service-account $SERVICE_ACCOUNT `
        --max-retries 1 `
        --task-timeout 10m
} else {
    Write-Host "  Creating new job..."
    & $gcloud run jobs create $JOB_NAME `
        --image $IMAGE `
        --region $REGION `
        --project $PROJECT_ID `
        --service-account $SERVICE_ACCOUNT `
        --max-retries 1 `
        --task-timeout 10m
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create/update Cloud Run Job"
    exit 1
}
Write-Host "  OK: Cloud Run Job ready"

# Create Cloud Scheduler
Write-Host ""
Write-Host "[5/5] Creating/updating Cloud Scheduler..."
$jobUri = "https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run"

$schedulerExists = & $gcloud scheduler jobs describe $SCHEDULER_NAME --location $REGION --project $PROJECT_ID 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Scheduler exists, updating schedule..."
    & $gcloud scheduler jobs update http $SCHEDULER_NAME `
        --location $REGION `
        --project $PROJECT_ID `
        --schedule $DAILY_CRON
} else {
    Write-Host "  Creating new scheduler..."
    & $gcloud scheduler jobs create http $SCHEDULER_NAME `
        --location $REGION `
        --project $PROJECT_ID `
        --schedule $DAILY_CRON `
        --uri $jobUri `
        --http-method POST `
        --oauth-service-account-email $SERVICE_ACCOUNT
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Failed to create/update scheduler"
} else {
    Write-Host "  OK: Cloud Scheduler configured"
}

Write-Host ""
Write-Host "=================================================================================="
Write-Host "DEPLOYMENT COMPLETE!"
Write-Host "=================================================================================="
Write-Host ""
Write-Host "✅ NEW Job: $JOB_NAME"
Write-Host "✅ Purpose: Updates ONLY Drunken Cookies sheet"
Write-Host "✅ Schedule: Daily at 1 AM Puerto Rico (5 AM UTC)"
Write-Host ""
Write-Host "⚠️  NOTE: This is SEPARATE from inventory-updater"
Write-Host "   - inventory-updater: Updates primary inventory sheet"
Write-Host "   - drunken-cookies-daily: Updates ONLY Drunken Cookies sheet"
Write-Host ""
Write-Host "View job:"
Write-Host "  https://console.cloud.google.com/run/jobs?project=$PROJECT_ID"
Write-Host ""
Write-Host "Test run:"
Write-Host "  gcloud run jobs execute $JOB_NAME --region $REGION --project $PROJECT_ID"
