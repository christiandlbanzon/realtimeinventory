# Check Cloud Run Job status and recent executions

$PROJECT_ID = "boxwood-chassis-332307"
$REGION = "us-east1"
$JOB_NAME = "inventory-updater"
$SCHEDULER_NAME = "${JOB_NAME}-schedule"

Write-Host "=================================================================================="
Write-Host "CLOUD RUN JOB STATUS CHECK"
Write-Host "=================================================================================="
Write-Host "Project: $PROJECT_ID"
Write-Host "Job: $JOB_NAME"
Write-Host "Region: $REGION"
Write-Host ""

# Check scheduler
Write-Host "[1] Cloud Scheduler Status:"
Write-Host ""
gcloud scheduler jobs describe $SCHEDULER_NAME --location $REGION --project $PROJECT_ID --format="table(name,schedule,state,lastAttemptTime,scheduleTime)"

Write-Host ""
Write-Host "[2] Recent Job Executions (last 5):"
Write-Host ""
gcloud run jobs executions list --job $JOB_NAME --region $REGION --project $PROJECT_ID --limit 5 --format="table(name,createTime,completionTime,status.conditions[0].type,status.conditions[0].status)"

Write-Host ""
Write-Host "[3] Latest Execution Logs:"
Write-Host ""
$latestExecution = gcloud run jobs executions list --job $JOB_NAME --region $REGION --project $PROJECT_ID --limit 1 --format="value(name)"
if ($latestExecution) {
    Write-Host "Execution: $latestExecution"
    Write-Host ""
    gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=$JOB_NAME AND labels.`"run.googleapis.com/execution_name`"=`"$latestExecution`"" --limit 10 --format="table(timestamp,textPayload)" --project $PROJECT_ID --freshness=1d
}

Write-Host ""
Write-Host "=================================================================================="
Write-Host "Job Console:"
Write-Host "  https://console.cloud.google.com/run/jobs?project=$PROJECT_ID"
Write-Host ""
Write-Host "Scheduler Console:"
Write-Host "  https://console.cloud.google.com/cloudscheduler?project=$PROJECT_ID"
Write-Host "=================================================================================="
