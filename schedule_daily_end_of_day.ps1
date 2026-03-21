# Switch Cloud Scheduler to run once per day at end of day (1 AM Puerto Rico = 5 AM UTC).
# The inventory script treats "before 6 AM" as "process yesterday", so this run finalizes the previous day.

$ErrorActionPreference = "Stop"
$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""

$PROJECT_ID = "boxwood-chassis-332307"
$REGION = "us-east1"
$JOB_NAME = "inventory-updater"
$SCHEDULER_NAME = "${JOB_NAME}-schedule"

# 5 AM UTC = 1 AM Puerto Rico (America/Puerto_Rico) - "end of day" run to finalize yesterday
$DAILY_CRON = "0 5 * * *"

Write-Host "=================================================================================="
Write-Host "SCHEDULER: Switch to daily end-of-day run"
Write-Host "=================================================================================="
Write-Host "Project: $PROJECT_ID"
Write-Host "Scheduler: $SCHEDULER_NAME"
Write-Host "New schedule: $DAILY_CRON (1 AM Puerto Rico = 5 AM UTC)"
Write-Host ""

$gcloud = "gcloud"
if (Test-Path "C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd") {
    $gcloud = "C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
}

Write-Host "[1/2] Updating Cloud Scheduler job to run once daily..."
& $gcloud scheduler jobs update http $SCHEDULER_NAME `
    --location $REGION `
    --project $PROJECT_ID `
    --schedule $DAILY_CRON

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "If the scheduler does not exist yet, create it:"
    Write-Host "  & `$gcloud scheduler jobs create http $SCHEDULER_NAME ``"
    Write-Host "    --location $REGION --project $PROJECT_ID ``"
    Write-Host "    --schedule '$DAILY_CRON' ``"
    Write-Host "    --uri https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/$JOB_NAME`:run ``"
    Write-Host "    --http-method POST ``"
    Write-Host "    --oauth-service-account-email 703996360436-compute@developer.gserviceaccount.com"
    exit 1
}

Write-Host ""
Write-Host "[2/2] Done. Scheduler now runs once per day at 1 AM Puerto Rico (5 AM UTC)."
Write-Host ""
Write-Host "Verify: https://console.cloud.google.com/cloudscheduler?project=$PROJECT_ID"
Write-Host "Manual run: gcloud run jobs execute $JOB_NAME --region $REGION --project $PROJECT_ID"
