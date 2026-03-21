#!/bin/bash
# Quick deployment script for fixes
# Run this from a machine with gcloud CLI installed

echo "=========================================="
echo "DEPLOYING FIXES TO VM"
echo "=========================================="

VM_NAME="inventory-updater-vm"
VM_ZONE="us-central1-a"
SCRIPT_FILE="vm_inventory_updater.py"

echo ""
echo "[1/4] Backing up current script on VM..."
gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="cd /home/banzo && cp $SCRIPT_FILE ${SCRIPT_FILE}.backup.\$(date +%Y%m%d_%H%M%S) && echo 'Backup created'"

echo ""
echo "[2/4] Uploading fixed script..."
gcloud compute scp $SCRIPT_FILE $VM_NAME:/home/banzo/$SCRIPT_FILE --zone=$VM_ZONE

echo ""
echo "[3/4] Verifying file..."
gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="ls -lh /home/banzo/$SCRIPT_FILE"

echo ""
echo "[4/4] Checking fixes are present..."
gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="grep -q 'FIX: Only use fallback if API actually failed' /home/banzo/$SCRIPT_FILE && echo '✅ San Patricio fix found' || echo '❌ San Patricio fix NOT found'"
gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="grep -q 'LARGE DISCREPANCY DETECTED' /home/banzo/$SCRIPT_FILE && echo '✅ Validation fix found' || echo '❌ Validation fix NOT found'"

echo ""
echo "=========================================="
echo "DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "Monitor logs with:"
echo "  gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command='tail -f /home/banzo/inventory_cron.log'"
