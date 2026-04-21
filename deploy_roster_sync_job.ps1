# Deploy Cloud Run Job: inventory-roster-sync (python sync_roster_week_job.py)
$ErrorActionPreference = "Stop"
$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""

$PROJECT_ID = "boxwood-chassis-332307"
$REGION = "us-east1"
$JOB_NAME = "inventory-roster-sync"
$SERVICE_ACCOUNT = "703996360436-compute@developer.gserviceaccount.com"
$IMAGE = "gcr.io/${PROJECT_ID}/${JOB_NAME}"

$gcloud = (Get-Command gcloud -ErrorAction SilentlyContinue).Source
if (-not $gcloud) {
    foreach ($path in @(
        "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    )) {
        if (Test-Path $path) { $gcloud = $path; break }
    }
}
if (-not $gcloud) { Write-Host "ERROR: gcloud not found"; exit 1 }

Write-Host "Building roster image: $IMAGE"
& $gcloud builds submit . --project $PROJECT_ID --config cloudbuild.roster.yaml
if ($LASTEXITCODE -ne 0) { exit 1 }

$jobExists = & $gcloud run jobs describe $JOB_NAME --region $REGION --project $PROJECT_ID 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "Updating job $JOB_NAME..."
    & $gcloud run jobs update $JOB_NAME `
        --image $IMAGE `
        --region $REGION `
        --project $PROJECT_ID `
        --service-account $SERVICE_ACCOUNT `
        --max-retries 1 `
        --task-timeout 30m `
        --command python `
        --args sync_roster_week_job.py
} else {
    Write-Host "Creating job $JOB_NAME..."
    & $gcloud run jobs create $JOB_NAME `
        --image $IMAGE `
        --region $REGION `
        --project $PROJECT_ID `
        --service-account $SERVICE_ACCOUNT `
        --max-retries 1 `
        --task-timeout 30m `
        --command python `
        --args sync_roster_week_job.py
}
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host "Done. Test: gcloud run jobs execute $JOB_NAME --region $REGION --project $PROJECT_ID"
