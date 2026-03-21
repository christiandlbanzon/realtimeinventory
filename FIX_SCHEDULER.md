# Fix Scheduler - Manual Steps

## Problem
The scheduler is ENABLED but shows "Next run time: Not scheduled" and has never attempted to run.

## Solution: Fix Permissions via Console

### Step 1: Grant Cloud Run Invoker Permission

1. Go to Cloud Run Jobs:
   https://console.cloud.google.com/run/jobs?project=boxwood-chassis-332307

2. Click on `inventory-updater`

3. Click the "PERMISSIONS" tab at the top

4. Click "GRANT ACCESS"

5. Add:
   - **Principal**: `703996360436-compute@developer.gserviceaccount.com`
   - **Role**: `Cloud Run Invoker`

6. Click "SAVE"

### Step 2: Verify Scheduler

1. Go to Cloud Scheduler:
   https://console.cloud.google.com/cloudscheduler?project=boxwood-chassis-332307

2. Click on `inventory-updater-schedule`

3. Verify:
   - **State**: Should be "ENABLED"
   - **Schedule**: `*/5 * * * *` (every 5 minutes)
   - **Next run time**: Should show a future time

4. If "Next run time" is still "Not scheduled":
   - Click "EDIT"
   - Click "SAVE" (even without changes) - this forces it to reschedule

### Step 3: Test

After fixing permissions, you can:

1. **Wait 5 minutes** - scheduler should trigger automatically
2. **Or manually trigger** via Console:
   - Go to Cloud Run Jobs
   - Click `inventory-updater`
   - Click "EXECUTE"

## Alternative: Use gcloud CLI

If you have gcloud CLI authenticated:

```bash
gcloud run jobs add-iam-policy-binding inventory-updater \
  --region=us-east1 \
  --member=serviceAccount:703996360436-compute@developer.gserviceaccount.com \
  --role=roles/run.invoker
```

## Why This Happened

The scheduler's service account needs explicit permission to invoke Cloud Run Jobs. This is a security feature - even though the scheduler uses the same service account, it needs the `run.invoker` role to trigger executions.
