@echo off
echo ================================================================================
echo RUNNING VM FIX
echo ================================================================================
echo.

cd /d "%~dp0"

echo Executing fix script on VM...
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && python3 apply_fix_on_vm.py"

echo.
echo ================================================================================
echo VERIFYING FIX
echo ================================================================================
echo.

gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="grep -A 5 'FIX FOR PROMOTION ITEMS' /home/banzo/vm_inventory_updater.py"

echo.
echo Done!
pause
