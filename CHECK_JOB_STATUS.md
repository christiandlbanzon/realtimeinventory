# Check Why Job Didn't Update Sheet

## Current Status
- ✅ Tab "2-2" exists (for February 2nd)
- ❌ "Live Sales Data" column shows all zeros
- ✅ Job executed successfully at 12:26:29 UTC (8:26 AM PR time)
- ❓ Need to check logs to see what happened

## Possible Reasons
1. **No sales data** - Clover API returned no sales for today
2. **Job error** - Job ran but encountered an error updating the sheet
3. **Wrong tab** - Job updated a different tab
4. **Wrong column** - Job updated a different column
5. **Time zone issue** - Job processed wrong date

## How to Check

### Option 1: View Logs in Console (BEST)
1. Go to: https://console.cloud.google.com/run/jobs/inventory-updater/executions?project=boxwood-chassis-332307&location=us-east1
2. Click on the execution (the one that succeeded)
3. Click "LOGS" tab
4. Look for:
   - Which tab it tried to update
   - Any errors
   - Sales data it found
   - What it wrote to the sheet

### Option 2: Check Cloud Logging
1. Go to: https://console.cloud.google.com/logs/query?project=boxwood-chassis-332307
2. Use this filter:
   ```
   resource.type="cloud_run_job"
   resource.labels.job_name="inventory-updater"
   ```
3. Look for error messages or what the job did

### Option 3: Manually Trigger Job
Run: `python trigger_job.py`
Then check the logs immediately after

## What to Look For in Logs
- "Desired tab: 2-2" - confirms it's looking for the right tab
- "Using existing tab: 2-2" - confirms it found the tab
- "Updated [store] sales" - shows it found sales data
- Any ERROR messages
- "Script completed successfully" - confirms it finished

## Next Steps
1. Check the logs to see what happened
2. If there are errors, fix them
3. If no sales data, verify Clover API is returning data
4. Manually trigger job and watch logs in real-time
