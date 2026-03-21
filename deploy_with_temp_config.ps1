# Deploy to Cloud Run - Using temp config to avoid permission issues

$env:CLOUDSDK_CONFIG = "$env:TEMP\gcloud_config"
$GCLOUD = "C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$PROJECT_ID = "boxwood-chassis-332307"
$REGION = "us-east1"
$JOB_NAME = "inventory-updater"

Write-Host "=================================================================================="
Write-Host "DEPLOYING TO CLOUD RUN"
Write-Host "=================================================================================="
Write-Host ""
Write-Host "Job: $JOB_NAME"
Write-Host "Region: $REGION"
Write-Host "Project: $PROJECT_ID"
Write-Host ""

# Set project
Write-Host "[1/4] Setting project..."
& $GCLOUD config set project $PROJECT_ID
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to set project"
    exit 1
}
Write-Host "OK: Project set"
Write-Host ""

# Authenticate using service account
Write-Host "[2/4] Authenticating with service account..."
& $GCLOUD auth activate-service-account --key-file=service-account-key.json
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Service account auth failed, trying default auth..."
}
Write-Host ""

# Build Docker image (Cloud Build - no local Docker needed!)
Write-Host "[3/4] Building Docker image..."
Write-Host "This builds in Google Cloud - you don't need Docker installed locally!"
Write-Host "This will take 3-5 minutes..."
Write-Host ""
& $GCLOUD builds submit --tag gcr.io/$PROJECT_ID/$JOB_NAME
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Build failed"
    exit 1
}
Write-Host ""
Write-Host "OK: Docker image built!"
Write-Host ""

# Create Cloud Run Job
Write-Host "[4/4] Creating Cloud Run Job..."
& $GCLOUD run jobs create $JOB_NAME `
    --image gcr.io/$PROJECT_ID/$JOB_NAME `
    --region $REGION `
    --service-account 703996360436-compute@developer.gserviceaccount.com `
    --max-retries 1 `
    --task-timeout 10m

if ($LASTEXITCODE -ne 0) {
    if ($LASTEXITCODE -eq 1) {
        Write-Host "Job might already exist, trying to update..."
        & $GCLOUD run jobs update $JOB_NAME `
            --image gcr.io/$PROJECT_ID/$JOB_NAME `
            --region $REGION
    } else {
        Write-Host "ERROR: Failed to create job"
        exit 1
    }
}
Write-Host "OK: Cloud Run Job created!"
Write-Host ""

# Create Cloud Scheduler
Write-Host "Creating Cloud Scheduler (runs every 5 minutes)..."
$JOB_URI = "https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/$JOB_NAME`:run"

& $GCLOUD scheduler jobs create http ${JOB_NAME}-schedule `
    --location $REGION `
    --schedule "*/5 * * * *" `
    --uri $JOB_URI `
    --http-method POST `
    --oauth-service-account-email 703996360436-compute@developer.gserviceaccount.com

if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Scheduler might already exist or failed to create"
    Write-Host "You can create it manually later"
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
