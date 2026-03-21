# Cloud Run Job Status Summary

## Job Configuration

- **Project:** `boxwood-chassis-332307`
- **Job Name:** `inventory-updater`
- **Region:** `us-east1`
- **Schedule:** Daily at **1:00 AM Puerto Rico** (5:00 AM UTC)
- **Cron:** `0 5 * * *`
- **Status:** ✅ ENABLED

## Recent Execution History

- **Last Run:** Feb 6, 2026 at 5:00 AM UTC (1:00 AM Puerto Rico) - ✅ SUCCESS
- **Next Run:** Feb 7, 2026 at 5:00 AM UTC (1:00 AM Puerto Rico)

## What the Job Does

Each daily run at 1 AM Puerto Rico:
1. Processes **yesterday's** sales data (early morning logic)
2. Fetches Clover/Shopify sales for yesterday
3. Updates **primary inventory sheet** (February sheet)
4. Updates **Drunken Cookies sheet** with all locations:
   - ✅ Plaza (Plaza Las Americas)
   - ✅ PlazaSol (Plaza del Sol)
   - ✅ VSJ (Old San Juan)
   - ✅ San Patricio
   - ✅ Montehiedra
   - ✅ Plaza Carolina

## Console Links

- **Cloud Run Jobs:** https://console.cloud.google.com/run/jobs?project=boxwood-chassis-332307
- **Cloud Scheduler:** https://console.cloud.google.com/cloudscheduler?project=boxwood-chassis-332307
- **Drunken Cookies Sheet:** https://docs.google.com/spreadsheets/d/1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE/edit

## Manual Test Run

To test the job manually (runs immediately):

```bash
gcloud run jobs execute inventory-updater --region us-east1 --project boxwood-chassis-332307
```

Or use PowerShell:
```powershell
cd "e:\prog fold\Drunken cookies\real-time-inventory"
.\run_job_manually.ps1
```

## Troubleshooting

### Job didn't run today?

1. **Check the time:** The job runs at **1:00 AM Puerto Rico** (5:00 AM UTC). If it's before that time, it hasn't run yet.

2. **Check the project:** Make sure you're looking at project `boxwood-chassis-332307`, not "Drunken Cookies Automations"

3. **Check scheduler status:**
   ```bash
   gcloud scheduler jobs describe inventory-updater-schedule --location us-east1 --project boxwood-chassis-332307
   ```

4. **Check recent executions:**
   ```bash
   gcloud run jobs executions list --job inventory-updater --region us-east1 --project boxwood-chassis-332307 --limit 5
   ```

5. **Check logs:**
   ```bash
   gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=inventory-updater" --limit 20 --project boxwood-chassis-332307 --freshness=1d
   ```

## Code Fixes Included

✅ **FOR_DATE support** - Backfill works correctly  
✅ **Location mapping** - Plaza, PlazaSol, VSJ write to Drunken Cookies  
✅ **Daily runs** - All locations update correctly  
