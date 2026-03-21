# Deploy to Cloud Run - Final version with proxy fix

# Disable proxy
$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""
$env:http_proxy = ""
$env:https_proxy = ""
$env:NO_PROXY = "*"

# Use temp config
$env:CLOUDSDK_CONFIG = "$env:TEMP\gcloud_config"

$GCLOUD = "C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$PROJECT_ID = "boxwood-chassis-332307"
$REGION = "us-east1"
$JOB_NAME = "inventory-updater"

Write-Host "=================================================================================="
Write-Host "DEPLOYING TO CLOUD RUN"
Write-Host "=================================================================================="
Write-Host ""
Write-Host "IMPORTANT: You do NOT need Docker installed locally!"
Write-Host "Google Cloud Build builds the image in the cloud."
Write-Host ""
Write-Host "Job: $JOB_NAME"
Write-Host "Region: $REGION"
Write-Host "Project: $PROJECT_ID"
Write-Host ""

# Set project
Write-Host "[1/5] Setting project..."
& $GCLOUD config set project $PROJECT_ID 2>&1 | Out-Null
Write-Host "OK: Project set"
Write-Host ""

# Authenticate using service account
Write-Host "[2/5] Authenticating with service account..."
& $GCLOUD auth activate-service-account --key-file=service-account-key.json --quiet 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: Authenticated with service account"
} else {
    Write-Host "WARNING: Service account auth failed"
    Write-Host "You may need to run: gcloud auth login"
    Write-Host "Continuing anyway..."
}
Write-Host ""

# Enable required APIs
Write-Host "[3/5] Enabling required APIs..."
& $GCLOUD services enable cloudbuild.googleapis.com --quiet 2>&1 | Out-Null
& $GCLOUD services enable run.googleapis.com --quiet 2>&1 | Out-Null
& $GCLOUD services enable cloudscheduler.googleapis.com --quiet 2>&1 | Out-Null
Write-Host "OK: APIs enabled"
Write-Host ""

# Build Docker image (Cloud Build - no local Docker needed!)
Write-Host "[4/5] Building Docker image..."
Write-Host "This builds in Google Cloud - you don't need Docker installed locally!"
Write-Host "This will take 3-5 minutes..."
Write-Host ""
& $GCLOUD builds submit --tag gcr.io/$PROJECT_ID/$JOB_NAME
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Build failed"
    Write-Host ""
    Write-Host "Possible issues:"
    Write-Host "  1. Not authenticated - run: gcloud auth login"
    Write-Host "  2. APIs not enabled - check console"
    Write-Host "  3. Network/proxy issues"
    Write-Host ""
    Write-Host "You can also deploy manually via Cloud Shell:"
    Write-Host "  https://shell.cloud.google.com/"
    exit 1
}
Write-Host ""
Write-Host "OK: Docker image built!"
Write-Host ""

# Create Cloud Run Job
Write-Host "[5/5] Creating Cloud Run Job..."
& $GCLOUD run jobs create $JOB_NAME `
    --image gcr.io/$PROJECT_ID/$JOB_NAME `
    --region $REGION `
    --service-account 703996360436-compute@developer.gserviceaccount.com `
    --max-retries 1 `
    --task-timeout 10m `
    --quiet 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "Job might already exist, updating..."
    & $GCLOUD run jobs update $JOB_NAME `
        --image gcr.io/$PROJECT_ID/$JOB_NAME `
        --region $REGION `
        --quiet 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK: Cloud Run Job updated!"
    } else {
        Write-Host "ERROR: Failed to create/update job"
        exit 1
    }
} else {
    Write-Host "OK: Cloud Run Job created!"
}
Write-Host ""

# Create Cloud Scheduler
Write-Host "Creating Cloud Scheduler (runs every 5 minutes)..."
$JOB_URI = "https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/$JOB_NAME`:run"

& $GCLOUD scheduler jobs create http ${JOB_NAME}-schedule `
    --location $REGION `
    --schedule "*/5 * * * *" `
    --uri $JOB_URI `
    --http-method POST `
    --oauth-service-account-email 703996360436-compute@developer.gserviceaccount.com `
    --quiet 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "Scheduler might already exist or failed"
    Write-Host "You can create it manually later if needed"
} else {
    Write-Host "OK: Cloud Scheduler created!"
}

Write-Host ""
Write-Host "=================================================================================="
Write-Host "DEPLOYMENT COMPLETE!"
Write-Host "=================================================================================="
Write-Host ""
Write-Host "View in Console:"
Write-Host "  Jobs: https://console.cloud.google.com/run/jobs?project=$PROJECT_ID"
Write-Host "  Scheduler: https://console.cloud.google.com/cloudscheduler?project=$PROJECT_ID"
Write-Host ""
Write-Host "Test run:"
Write-Host "  & `$GCLOUD run jobs execute $JOB_NAME --region $REGION"
