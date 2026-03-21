# Final Checklist - Getting Scheduler to Work

## What We've Fixed ✅

1. ✅ **URI Format**: Updated from v1 to v2 API format
2. ✅ **Cloud Run Invoker**: Granted to service account
3. ✅ **Service Account Token Creator**: Should be granted (you just did this)

## Current Issue

Scheduler shows:
- "Last attempt: Never" 
- "Next run: Not scheduled"

This means it hasn't tried to run since we made changes.

## Steps to Fix

### Step 1: Verify Roles Are Granted
Go to: https://console.cloud.google.com/iam-admin/iam?project=boxwood-chassis-332307

Check that `703996360436-compute@developer.gserviceaccount.com` has BOTH:
- ✅ Cloud Run Invoker
- ✅ Service Account Token Creator

### Step 2: Manually Trigger Scheduler (TEST)
1. Go to: https://console.cloud.google.com/cloudscheduler?project=boxwood-chassis-332307
2. Click `inventory-updater-schedule`
3. Look for a "RUN NOW" or "TEST" button
4. Click it to manually trigger
5. Wait 30 seconds
6. Check if status changes to "Succeeded"

### Step 3: Reschedule Scheduler
If manual trigger works:
1. Go back to scheduler list
2. Click `inventory-updater-schedule`
3. Click "EDIT"
4. Click "UPDATE" (to reschedule)
5. Check that "Next run" shows a future time

### Step 4: Verify It's Working
Wait 5-10 minutes, then check:
- Cloud Scheduler: Status should show "Succeeded"
- Cloud Run Jobs: New executions every 5 minutes

## If Still Failing

Check Cloud Logging for detailed error:
1. Go to: https://console.cloud.google.com/logs/query?project=boxwood-chassis-332307
2. Use filter:
   ```
   resource.type="cloud_scheduler_job"
   resource.labels.job_id="inventory-updater-schedule"
   ```
3. Look for the most recent error message
4. Share the error details

## Alternative: Use Different Authentication Method

If OIDC tokens keep failing, we could:
1. Use Pub/Sub instead of HTTP target
2. Or use a different service account
3. Or configure authentication differently

But let's try the manual trigger first to see if it works now!
