# ERROR HANDLING GUIDE - VM Inventory Updater

## ✅ CURRENT STATUS

**Cron Job**: ✅ Configured to run every 5 minutes
```
*/5 * * * * cd /home/banzo && export INVENTORY_SHEET_ID=1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno && /home/banzo/venv/bin/python vm_inventory_updater.py >> inventory_cron.log 2>&1
```

**Sheet ID**: ✅ November sheet (correct)

**Last Run**: ✅ Script is running successfully

---

## 🔍 HOW TO CHECK STATUS

### Quick Status Check
```bash
# Check if cron is configured
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="crontab -l"

# Check recent runs
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -50 /home/banzo/inventory_cron.log | grep 'Script completed' | tail -5"

# Check for errors
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -100 /home/banzo/inventory_cron.log | grep -i ERROR | tail -10"
```

### Detailed Status Check
```bash
# Full log tail
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -100 /home/banzo/inventory_cron.log"

# Check column detection
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -200 /home/banzo/inventory_cron.log | grep 'Location columns found'"

# Check if script is running
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="ps aux | grep vm_inventory"
```

---

## ⚠️ COMMON ERRORS & SOLUTIONS

### 1. Script Not Running

**Symptoms:**
- No new log entries
- No updates in Google Sheet

**Check:**
```bash
# Check cron job
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="crontab -l"

# Check cron service
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="sudo service cron status"
```

**Fix:**
```bash
# Restart cron service
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="sudo service cron restart"

# Or manually run script to test
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && export INVENTORY_SHEET_ID=1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno && /home/banzo/venv/bin/python vm_inventory_updater.py"
```

### 2. Column Detection Errors

**Symptoms:**
- Log shows: `Location columns found: {}` (empty)
- Log shows: `No updates to make`

**Check:**
```bash
# Check column detection
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -200 /home/banzo/inventory_cron.log | grep -i 'location columns found\|Found.*Live Sales Data'"
```

**Fix:**
- The script should detect all 6 locations
- If not detected, check Google Sheet structure
- Verify "Live Sales Data (Do Not Touch)" headers exist

### 3. API Connection Errors

**Symptoms:**
- Log shows: `ERROR: API returned status XXX`
- Log shows: `Error fetching Clover data`

**Check:**
```bash
# Check API errors
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -200 /home/banzo/inventory_cron.log | grep -i 'API.*error\|connection\|timeout'"
```

**Fix:**
- Check internet connectivity on VM
- Verify API credentials are valid
- Check API rate limits

### 4. Google Sheets Errors

**Symptoms:**
- Log shows: `Error updating sheet`
- Log shows: `Permission denied`

**Check:**
```bash
# Check sheet errors
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -200 /home/banzo/inventory_cron.log | grep -i 'sheet\|permission\|403\|401'"
```

**Fix:**
- Verify service account has access to sheet
- Check sheet ID is correct
- Verify sheet exists and is accessible

### 5. Data Quality Warnings

**Symptoms:**
- Log shows: `SUSPICIOUS VALUE DETECTED`
- Log shows: `Validation warnings`

**Note:** These are warnings, not errors. The script will still run but may skip suspicious data.

**Check:**
```bash
# Check validation warnings
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -200 /home/banzo/inventory_cron.log | grep -i 'suspicious\|warning\|validation'"
```

---

## 🛠️ TROUBLESHOOTING STEPS

### Step 1: Check Recent Logs
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a \
  --command="tail -100 /home/banzo/inventory_cron.log"
```

### Step 2: Check for Errors
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a \
  --command="tail -500 /home/banzo/inventory_cron.log | grep -i ERROR | tail -20"
```

### Step 3: Test Manual Run
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a \
  --command="cd /home/banzo && export INVENTORY_SHEET_ID=1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno && /home/banzo/venv/bin/python vm_inventory_updater.py"
```

### Step 4: Verify Cron is Running
```bash
# Check cron job exists
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="crontab -l"

# Check cron service
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="sudo service cron status"

# Restart cron if needed
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="sudo service cron restart"
```

### Step 5: Check VM Status
```bash
# Check if VM is running
gcloud compute instances describe inventory-updater-vm --zone=us-central1-a --format="get(status)"

# Check VM resources
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="df -h && free -h"
```

---

## 📊 MONITORING SCHEDULE

### Daily Checks (Recommended)
1. Check logs for errors: `tail -100 inventory_cron.log | grep ERROR`
2. Verify script ran: `tail -100 inventory_cron.log | grep "Script completed"`
3. Check column detection: `grep "Location columns found" inventory_cron.log | tail -1`

### Weekly Checks
1. Review data quality warnings
2. Check API connectivity
3. Verify all 6 locations are updating

---

## 🚨 EMERGENCY PROCEDURES

### If Script Stops Running

1. **Check VM Status**
   ```bash
   gcloud compute instances describe inventory-updater-vm --zone=us-central1-a
   ```

2. **Restart Cron**
   ```bash
   gcloud compute ssh inventory-updater-vm --zone=us-central1-a \
     --command="sudo service cron restart"
   ```

3. **Manual Test Run**
   ```bash
   gcloud compute ssh inventory-updater-vm --zone=us-central1-a \
     --command="cd /home/banzo && export INVENTORY_SHEET_ID=1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno && /home/banzo/venv/bin/python vm_inventory_updater.py"
   ```

### If Data is Wrong

1. **Check Last Successful Run**
   ```bash
   gcloud compute ssh inventory-updater-vm --zone=us-central1-a \
     --command="tail -500 /home/banzo/inventory_cron.log | grep 'Script completed successfully' | tail -5"
   ```

2. **Review Column Detection**
   ```bash
   gcloud compute ssh inventory-updater-vm --zone=us-central1-a \
     --command="tail -500 /home/banzo/inventory_cron.log | grep 'Location columns found' | tail -5"
   ```

3. **Check API Data**
   ```bash
   gcloud compute ssh inventory-updater-vm --zone=us-central1-a \
     --command="tail -500 /home/banzo/inventory_cron.log | grep 'Sales data fetched' | tail -5"
   ```

---

## ✅ VERIFICATION COMMANDS

### Verify Everything is Working
```bash
# 1. Check cron is configured
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="crontab -l | grep vm_inventory"

# 2. Check recent successful runs (should see runs every 5 minutes)
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -200 /home/banzo/inventory_cron.log | grep 'Script completed successfully' | tail -10"

# 3. Verify column detection (should show all 6 locations)
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -200 /home/banzo/inventory_cron.log | grep 'Location columns found' | tail -1"

# 4. Check for errors (should be minimal)
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -500 /home/banzo/inventory_cron.log | grep -i ERROR | wc -l"
```

---

## 📞 QUICK REFERENCE

**VM Zone**: `us-central1-a`

**Log File**: `/home/banzo/inventory_cron.log`

**Script Location**: `/home/banzo/vm_inventory_updater.py`

**Python**: `/home/banzo/venv/bin/python`

**Sheet ID**: `1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno`

**Cron Schedule**: Every 5 minutes (`*/5 * * * *`)

---

Last Updated: November 5, 2025


