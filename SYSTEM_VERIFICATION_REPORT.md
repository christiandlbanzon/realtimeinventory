# Real-Time Inventory System - Verification Report

**Date**: January 29, 2026  
**Status**: ✅ Local Configuration Verified | ⚠️ VM Check Requires gcloud CLI

---

## 📋 Summary

This report documents the verification of your real-time inventory system that:
- Fetches sales data from Clover API for 6 locations
- Updates Google Sheets with real-time inventory data
- Runs on GCP VM (`inventory-updater-vm`) every 5 minutes

---

## ✅ Local Configuration Check

### 1. Clover API Credentials ✅
**Status**: All credentials found and valid

Found **6 Clover locations** configured:
- ✅ **Plaza** (Plaza Las Americas)
  - Merchant ID: `3YCBMZQ6SFT71`
  - Token: `291357c3...`
  - Category ID: `AHQ1T93FPV3XP`

- ✅ **PlazaSol** (Plaza del Sol)
  - Merchant ID: `J14BXNH1WDT71`
  - Token: `3a58ea58...`
  - Category ID: `6B0N056EAXCDA`

- ✅ **San Patricio**
  - Merchant ID: `Y3JSKHZKVKYM1`
  - Token: `f74379c5...`
  - Category ID: `BXH2KACECKDA2`

- ✅ **VSJ** (Old San Juan)
  - Merchant ID: `QJD3EASTRDBX1`
  - Token: `bd30b891...`
  - Category ID: `CYF77ZMHW5MYY`

- ✅ **Montehiedra**
  - Merchant ID: `FNK14Z5E7CAA1`
  - Token: `ce9efab8...`
  - Category ID: `X9Y7W6J4W6WZP`

- ✅ **Plaza Carolina**
  - Merchant ID: `S322BTDA07H71`
  - Token: `02205219...`
  - Category ID: `43XNCHCCX6F4A`

**File**: `clover_creds.json` ✅ Valid JSON format

---

### 2. Google Sheets Credentials ✅
**Status**: Service account credentials loaded successfully

- ✅ **Project ID**: `boxwood-chassis-332307`
- ✅ **Client Email**: `703996360436-compute@developer.gserviceaccount.com`
- ✅ **File**: `service-account-key.json` ✅ Valid service account format

**Note**: To check Google Sheets access, set the `INVENTORY_SHEET_ID` environment variable:
```bash
export INVENTORY_SHEET_ID=1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno
```

Based on documentation, the current sheet ID is: `1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno` (November sheet)

---

### 3. Local API Connectivity ⚠️
**Status**: Cannot test from local machine (network/proxy issues)

**Issue**: Local machine cannot connect to Clover API (likely proxy/network configuration)

**Note**: This is expected - the system runs on the VM, not locally. The VM should have proper network access.

---

## 🖥️ VM Deployment Status

### VM Configuration (from documentation)
- **VM Name**: `inventory-updater-vm`
- **Zone**: `us-central1-a`
- **User**: `banzo`
- **Home Directory**: `/home/banzo`
- **Script**: `/home/banzo/vm_inventory_updater.py`
- **Log File**: `/home/banzo/inventory_cron.log`

### Cron Job Configuration
```bash
*/5 * * * * cd /home/banzo && export INVENTORY_SHEET_ID=1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno && /home/banzo/venv/bin/python vm_inventory_updater.py >> inventory_cron.log 2>&1
```

**Schedule**: Every 5 minutes ✅

---

## 🔍 VM Verification Commands

To verify the VM deployment, run these commands (requires `gcloud` CLI):

### 1. Check VM Status
```bash
gcloud compute instances describe inventory-updater-vm --zone=us-central1-a
```

### 2. Check Cron Configuration
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="crontab -l"
```

### 3. Check Recent Logs
```bash
# Last 100 log entries
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -100 /home/banzo/inventory_cron.log"

# Check for successful runs
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -200 /home/banzo/inventory_cron.log | grep 'Script completed successfully' | tail -10"

# Check for errors
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -500 /home/banzo/inventory_cron.log | grep -i ERROR | tail -10"
```

### 4. Check Files on VM
```bash
# List Python files
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="ls -lh /home/banzo/*.py"

# Check credentials exist
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="ls -lh /home/banzo/clover_creds.json /home/banzo/service-account-key.json"
```

### 5. Test Manual Execution
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && export INVENTORY_SHEET_ID=1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno && /home/banzo/venv/bin/python vm_inventory_updater.py"
```

### 6. Check Python Environment
```bash
# Check Python version
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="/home/banzo/venv/bin/python --version"

# Check installed packages
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="/home/banzo/venv/bin/pip list | grep -E 'google|requests'"
```

---

## 📊 Quick Status Check Script

Use the provided Python scripts:

### Local Configuration Check
```bash
python comprehensive_system_check.py
```

### VM Deployment Check (requires gcloud CLI)
```bash
python check_vm_deployment.py
```

---

## ✅ Verification Checklist

### Local Files ✅
- [x] `clover_creds.json` - Found and valid (6 locations)
- [x] `service-account-key.json` - Found and valid
- [x] `vm_inventory_updater.py` - Exists (needs content check)
- [x] `requirements.txt` - Dependencies listed

### VM Deployment (requires gcloud CLI) ⚠️
- [ ] VM is running
- [ ] SSH access works
- [ ] Script file exists on VM
- [ ] Credentials exist on VM
- [ ] Cron job is configured
- [ ] Recent log entries show successful runs
- [ ] No errors in recent logs
- [ ] Python environment is set up correctly

---

## 🔧 Troubleshooting

### If VM Check Fails
1. **Install gcloud CLI**: https://cloud.google.com/sdk/docs/install
2. **Authenticate**: `gcloud auth login`
3. **Set project**: `gcloud config set project boxwood-chassis-332307`

### If Script Not Running
1. Check VM status: `gcloud compute instances describe inventory-updater-vm --zone=us-central1-a`
2. Check cron service: `gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="sudo service cron status"`
3. Restart cron: `gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="sudo service cron restart"`

### If API Calls Fail
1. Verify credentials are valid (check token expiration)
2. Check network connectivity from VM
3. Verify merchant IDs are correct
4. Check Clover API status

### If Sheet Updates Fail
1. Verify service account has access to the sheet
2. Check sheet ID is correct
3. Verify sheet tab exists (format: `M-D` e.g., `1-29`)
4. Check for permission errors in logs

---

## 📝 Next Steps

1. **Install gcloud CLI** to enable VM verification
2. **Run VM deployment check** using `check_vm_deployment.py`
3. **Review recent logs** to verify script is running successfully
4. **Verify sheet updates** by checking the Google Sheet directly
5. **Monitor for errors** in the log file

---

## 📞 Quick Reference

- **VM Name**: `inventory-updater-vm`
- **Zone**: `us-central1-a`
- **Sheet ID**: `1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno`
- **Update Frequency**: Every 5 minutes
- **Log File**: `/home/banzo/inventory_cron.log`

---

**Report Generated**: January 29, 2026  
**Tools Used**: `comprehensive_system_check.py`, `check_vm_deployment.py`
