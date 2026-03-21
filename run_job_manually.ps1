# Manually trigger Cloud Run Job execution (for testing)

$PROJECT_ID = "boxwood-chassis-332307"
$REGION = "us-east1"
$JOB_NAME = "drunken-cookies-daily"

Write-Host "=================================================================================="
Write-Host "MANUALLY TRIGGER CLOUD RUN JOB"
Write-Host "=================================================================================="
Write-Host "Job: $JOB_NAME"
Write-Host "Region: $REGION"
Write-Host "Project: $PROJECT_ID"
Write-Host ""
Write-Host "This will execute the job immediately (processes yesterday's data)..."
Write-Host ""

$gcloud = Get-Command gcloud -ErrorAction SilentlyContinue
if (-not $gcloud) {
    Write-Host "ERROR: gcloud not found"
    exit 1
}

Write-Host "Executing job..."
& gcloud run jobs execute $JOB_NAME --region $REGION --project $PROJECT_ID

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Job execution started!"
    Write-Host ""
    Write-Host "View execution logs:"
    Write-Host "  https://console.cloud.google.com/run/jobs?project=$PROJECT_ID"
} else {
    Write-Host ""
    Write-Host "❌ Failed to execute job"
}
