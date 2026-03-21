# Deploy Cloud Run Job - Daily Schedule

## Summary

Deploy the updated inventory updater as a Cloud Run Job that runs **daily at 1 AM Puerto Rico (5 AM UTC)** to process yesterday's data.

## What's Fixed

✅ **FOR_DATE support** - Backfill now works correctly  
✅ **Location mapping** - Plaza, PlazaSol, VSJ now write to Drunken Cookies sheet  
✅ **Daily runs** - All locations update correctly in daily runs  

## Deployment Steps

### 1. Build Docker Image

```bash
cd "e:\prog fold\Drunken cookies\real-time-inventory"
gcloud builds submit --tag gcr.io/boxwood-chassis-332307/inventory-updater --project boxwood-chassis-332307
```

### 2. Create/Update Cloud Run Job

**If job doesn't exist:**
```bash
gcloud run jobs create inventory-updater \
  --image gcr.io/boxwood-chassis-332307/inventory-updater \
  --region us-east1 \
  --project boxwood-chassis-332307 \
  --service-account 703996360436-compute@developer.gserviceaccount.com \
  --max-retries 1 \
  --task-timeout 10m
```

**If job already exists:**
```bash
gcloud run jobs update inventory-updater \
  --image gcr.io/boxwood-chassis-332307/inventory-updater \
  --region us-east1 \
  --project boxwood-chassis-332307 \
  --service-account 703996360436-compute@developer.gserviceaccount.com \
  --max-retries 1 \
  --task-timeout 10m
```

### 3. Create/Update Cloud Scheduler (Daily at 1 AM PR = 5 AM UTC)

**If scheduler doesn't exist:**
```bash
gcloud scheduler jobs create http inventory-updater-schedule \
  --location us-east1 \
  --project boxwood-chassis-332307 \
  --schedule "0 5 * * *" \
  --uri https://us-east1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/boxwood-chassis-332307/jobs/inventory-updater:run \
  --http-method POST \
  --oauth-service-account-email 703996360436-compute@developer.gserviceaccount.com
```

**If scheduler already exists:**
```bash
gcloud scheduler jobs update http inventory-updater-schedule \
  --location us-east1 \
  --project boxwood-chassis-332307 \
  --schedule "0 5 * * *"
```

## Schedule Details

- **Cron:** `0 5 * * *` = 5:00 AM UTC = 1:00 AM Puerto Rico
- **Behavior:** Runs once per day to process **yesterday's** data
- **Logic:** Script's "early morning" mode (before 6 AM) processes previous day
- **Updates:** Both primary inventory sheet AND Drunken Cookies sheet

## Test Run

Test the job manually:
```bash
gcloud run jobs execute inventory-updater --region us-east1 --project boxwood-chassis-332307
```

## Verify

- **Cloud Run Jobs:** https://console.cloud.google.com/run/jobs?project=boxwood-chassis-332307
- **Cloud Scheduler:** https://console.cloud.google.com/cloudscheduler?project=boxwood-chassis-332307
- **Drunken Cookies Sheet:** https://docs.google.com/spreadsheets/d/1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE/edit

## What Gets Updated

Each daily run:
1. Fetches Clover/Shopify sales for **yesterday**
2. Updates primary inventory sheet (February sheet)
3. Updates **Drunken Cookies sheet** with all locations:
   - Plaza (Plaza Las Americas)
   - PlazaSol (Plaza del Sol)
   - VSJ (Old San Juan)
   - San Patricio
   - Montehiedra
   - Plaza Carolina

## Troubleshooting

If deployment fails:
1. Check gcloud is authenticated: `gcloud auth list`
2. Check project is set: `gcloud config set project boxwood-chassis-332307`
3. Check service account has permissions
4. View logs: `gcloud run jobs executions list --job inventory-updater --region us-east1`
