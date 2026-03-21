# Deploy to Cloud Run - Step by Step Instructions

## Why Cloud Run?
- ✅ Pay only when running (~$0.50/month vs $7-10/month for VM)
- ✅ No API timeout issues
- ✅ Fully managed - no server maintenance
- ✅ Modern GCP best practice for scheduled tasks

## Method: Use Google Cloud Shell (Easiest - No Installation Needed)

### Step 1: Open Cloud Shell
1. Go to: https://shell.cloud.google.com/
2. Make sure project is set: `boxwood-chassis-332307`
3. If not, run: `gcloud config set project boxwood-chassis-332307`

### Step 2: Upload Files
In Cloud Shell, click the **"Upload"** button (folder icon with up arrow) and upload:
- `vm_inventory_updater_fixed.py`
- `clover_creds.json`
- `service-account-key.json`
- `Dockerfile` (created for you)

### Step 3: Build and Deploy
Run these commands in Cloud Shell:

```bash
# Build Docker image
gcloud builds submit --tag gcr.io/boxwood-chassis-332307/inventory-updater

# Create Cloud Run Job
gcloud run jobs create inventory-updater \
  --image gcr.io/boxwood-chassis-332307/inventory-updater \
  --region us-east1 \
  --service-account 703996360436-compute@developer.gserviceaccount.com \
  --max-retries 1 \
  --task-timeout 10m

# Create Cloud Scheduler (runs every 5 minutes)
gcloud scheduler jobs create http inventory-updater-schedule \
  --location us-east1 \
  --schedule '*/5 * * * *' \
  --uri https://us-east1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/boxwood-chassis-332307/jobs/inventory-updater:run \
  --http-method POST \
  --oauth-service-account-email 703996360436-compute@developer.gserviceaccount.com
```

### Step 4: Verify
```bash
# Test run manually
gcloud run jobs execute inventory-updater --region us-east1

# Check logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=inventory-updater" --limit 50
```

## View in Console
- Jobs: https://console.cloud.google.com/run/jobs?project=boxwood-chassis-332307
- Scheduler: https://console.cloud.google.com/cloudscheduler?project=boxwood-chassis-332307

## That's It!
Your script will now run automatically every 5 minutes, and you only pay for execution time (~30 seconds every 5 minutes).
