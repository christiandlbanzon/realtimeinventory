@echo off
REM Batch script to execute deployment on VM
REM This runs the deployment script that's already in VM metadata

echo ========================================
echo DEPLOYING TO VM
echo ========================================
echo.
echo VM: real-time-inventory
echo Zone: us-central1-a
echo Project: boxwood-chassis-332307
echo.

echo Executing deployment script...
echo.

gcloud compute ssh real-time-inventory --zone=us-central1-a --project=boxwood-chassis-332307 --command="curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-and-setup | bash"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo DEPLOYMENT COMPLETE!
    echo ========================================
    echo.
    echo Files should now be deployed on the VM.
    echo Cron job should be set up to run every 5 minutes.
    echo.
    echo To verify, SSH to the VM and check:
    echo   gcloud compute ssh real-time-inventory --zone=us-central1-a --project=boxwood-chassis-332307
    echo   ls -lh /home/banzo/
    echo   crontab -l
) else (
    echo.
    echo ========================================
    echo ERROR
    echo ========================================
    echo.
    echo Error executing deployment.
    echo.
    echo You can try running manually:
    echo   gcloud compute ssh real-time-inventory --zone=us-central1-a --project=boxwood-chassis-332307
    echo   curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/deploy-and-setup ^| bash
)

pause
