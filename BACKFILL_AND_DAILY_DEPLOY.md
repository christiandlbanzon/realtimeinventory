# Backfill + Daily End-of-Day Deployment

## 1. Backfill missing data (after VM stopped)

From the `real-time-inventory` folder (with `clover_creds.json` and `service-account-key.json` in place):

```bash
# Backfill last 30 days (default)
python backfill_drunken_cookies.py

# Backfill a specific range
python backfill_drunken_cookies.py 2025-12-01 2025-12-29

# Preview only (no writes)
python backfill_drunken_cookies.py --dry-run 2025-12-01 2025-12-29
```

Each date runs the full updater: fetches Clover/Shopify sales for that day and writes to both the primary inventory sheet and the **Drunken Cookies** sheet.

---

## 2. Deploy as Cloud Run Job + run at end of day

### Option A: First-time deploy (job + daily schedule)

1. Build and push the image, create the job (same as before):
   ```bash
   gcloud config set project boxwood-chassis-332307
   gcloud builds submit --tag gcr.io/boxwood-chassis-332307/inventory-updater
   gcloud run jobs create inventory-updater \
     --image gcr.io/boxwood-chassis-332307/inventory-updater \
     --region us-east1 \
     --service-account 703996360436-compute@developer.gserviceaccount.com \
     --max-retries 1 \
     --task-timeout 10m
   ```

2. Create Cloud Scheduler to run **once per day** at 1 AM Puerto Rico (5 AM UTC):
   ```bash
   gcloud scheduler jobs create http inventory-updater-schedule \
     --location us-east1 \
     --schedule "0 5 * * *" \
     --uri "https://us-east1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/boxwood-chassis-332307/jobs/inventory-updater:run" \
     --http-method POST \
     --oauth-service-account-email 703996360436-compute@developer.gserviceaccount.com
   ```

### Option B: Job already exists – only switch to daily schedule

Run from `real-time-inventory`:

```powershell
.\schedule_daily_end_of_day.ps1
```

Or with gcloud:

```bash
gcloud scheduler jobs update http inventory-updater-schedule \
  --location us-east1 \
  --schedule "0 5 * * *"
```

---

## 3. Schedule behavior

- **Cron:** `0 5 * * *` = 5:00 AM UTC = 1:00 AM Puerto Rico.
- At that time the script’s “early morning” logic runs, so it processes **yesterday’s** data and updates both the primary sheet and the Drunken Cookies sheet.

---

## 4. Manual test

```bash
gcloud run jobs execute inventory-updater --region us-east1 --project boxwood-chassis-332307
```

---

## 5. Links

- [Cloud Run Jobs](https://console.cloud.google.com/run/jobs?project=boxwood-chassis-332307)
- [Cloud Scheduler](https://console.cloud.google.com/cloudscheduler?project=boxwood-chassis-332307)
- Drunken Cookies sheet: [link](https://docs.google.com/spreadsheets/d/1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE/edit?gid=512681683)
