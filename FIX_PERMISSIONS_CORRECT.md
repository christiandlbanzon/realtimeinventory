# Fix Scheduler Permissions - Correct Steps

## Method 1: Via Cloud Run Jobs Page (Easiest)

1. **Go to Cloud Run Jobs:**
   https://console.cloud.google.com/run/jobs?project=boxwood-chassis-332307

2. **Click on `inventory-updater`** (the job name)

3. **Click the "PERMISSIONS" tab** at the top of the job details page

4. **Click "GRANT ACCESS"** button

5. **Add:**
   - **New principals**: `703996360436-compute@developer.gserviceaccount.com`
   - **Select a role**: Choose `Cloud Run Invoker`
   - Click "SAVE"

## Method 2: Via IAM & Admin (Alternative)

1. **Go to IAM & Admin:**
   https://console.cloud.google.com/iam-admin/iam?project=boxwood-chassis-332307

2. **Click "GRANT ACCESS"** at the top

3. **Add:**
   - **New principals**: `703996360436-compute@developer.gserviceaccount.com`
   - **Select a role**: Search for `Cloud Run Invoker`
   - **Condition**: Leave empty
   - Click "SAVE"

## Method 3: Use gcloud CLI (If you have it)

```bash
gcloud run jobs add-iam-policy-binding inventory-updater \
  --region=us-east1 \
  --member=serviceAccount:703996360436-compute@developer.gserviceaccount.com \
  --role=roles/run.invoker \
  --project=boxwood-chassis-332307
```

## After Fixing Permissions

1. Go to Cloud Scheduler:
   https://console.cloud.google.com/cloudscheduler?project=boxwood-chassis-332307

2. Click `inventory-updater-schedule`

3. Click "EDIT" then "SAVE" (to reschedule)

4. Check that "Next run time" shows a future time

5. Wait 5 minutes - it should run automatically!
