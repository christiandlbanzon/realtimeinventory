# PowerShell script to execute deployment on VM
# This runs the deployment script that's already in VM metadata

$VM_NAME = "real-time-inventory"
$ZONE = "us-central1-a"
$PROJECT_ID = "boxwood-chassis-332307"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DEPLOYING TO VM" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "VM: $VM_NAME" -ForegroundColor Yellow
Write-Host "Zone: $ZONE" -ForegroundColor Yellow
Write-Host "Project: $PROJECT_ID" -ForegroundColor Yellow
Write-Host ""

# Command to execute deployment script from metadata
$deployCommand = "curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-and-setup | bash"

Write-Host "Executing deployment script..." -ForegroundColor Green
Write-Host ""

try {
    # Run gcloud compute ssh with the deployment command
    gcloud compute ssh $VM_NAME `
        --zone=$ZONE `
        --project=$PROJECT_ID `
        --command=$deployCommand
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "DEPLOYMENT COMPLETE!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Files should now be deployed on the VM." -ForegroundColor Yellow
    Write-Host "Cron job should be set up to run every 5 minutes." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To verify, SSH to the VM and check:" -ForegroundColor Cyan
    Write-Host "  gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT_ID" -ForegroundColor White
    Write-Host "  ls -lh /home/banzo/" -ForegroundColor White
    Write-Host "  crontab -l" -ForegroundColor White
    
} catch {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "ERROR" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error executing deployment: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "You can try running manually:" -ForegroundColor Yellow
    Write-Host "  gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT_ID" -ForegroundColor White
    Write-Host "  curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-and-setup | bash" -ForegroundColor White
    exit 1
}
