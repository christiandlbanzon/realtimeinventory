#!/usr/bin/env python3
"""
Create or replace Cloud Scheduler: **Friday 01:00 America/Puerto_Rico** → run Cloud Run Job
that should execute `python sync_roster_week_job.py`.

Cloud Run Job env (examples):
  - Default: ``ROSTER_SYNC_DAYS=7`` — seven days forward from run date.
  - Rest of month: ``ROSTER_SYNC_REST_OF_MONTH=1`` — **today → last day of current month** in PR
    only (no backfill from the 1st). Pair with ``SYNC_ROSTER_TARGETS=mall_pars,dispatch_pars`` as needed.

Edit PROJECT_ID, REGION, ROSTER_JOB_NAME, SERVICE_ACCOUNT_EMAIL to match your GCP project.

Disable any older *daily* roster scheduler so you do not double-run.
"""
from __future__ import annotations

import os
import sys

for proxy_var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(proxy_var, None)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service-account-key.json"

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

# --- edit for your project ---
PROJECT_ID = os.getenv("GCP_PROJECT", "boxwood-chassis-332307")
REGION = os.getenv("GCP_REGION", "us-east1")
# Cloud Run **Job** name that runs the roster image with command: python sync_roster_week_job.py
ROSTER_JOB_NAME = os.getenv("ROSTER_CLOUD_RUN_JOB", "inventory-roster-sync")
SERVICE_ACCOUNT_EMAIL = os.getenv(
    "SCHEDULER_SA_EMAIL",
    "703996360436-compute@developer.gserviceaccount.com",
)
SCHEDULER_JOB_ID = os.getenv("ROSTER_SCHEDULER_NAME", "inventory-roster-sync-weekly")
# Friday 01:00 in America/Puerto_Rico
CRON = "0 1 * * 5"

print("=" * 72)
print("CREATE / UPDATE CLOUD SCHEDULER — weekly roster (Friday 1am PR)")
print("=" * 72)
print(f"Project: {PROJECT_ID}")
print(f"Region: {REGION}")
print(f"Schedule: {CRON}  tz=America/Puerto_Rico  (Friday 1:00)")
print(f"Target: Cloud Run Job `{ROSTER_JOB_NAME}:run`")
print(f"Scheduler job id: {SCHEDULER_JOB_ID}\n")

credentials = service_account.Credentials.from_service_account_file(
    "service-account-key.json",
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
scheduler = build("cloudscheduler", "v1", http=authorized_http)

job_uri = (
    f"https://{REGION}-run.googleapis.com/apis/run.googleapis.com/v1/"
    f"namespaces/{PROJECT_ID}/jobs/{ROSTER_JOB_NAME}:run"
)

body = {
    "name": f"projects/{PROJECT_ID}/locations/{REGION}/jobs/{SCHEDULER_JOB_ID}",
    "schedule": CRON,
    "timeZone": "America/Puerto_Rico",
    "httpTarget": {
        "uri": job_uri,
        "httpMethod": "POST",
        "oidcToken": {"serviceAccountEmail": SERVICE_ACCOUNT_EMAIL},
    },
}

parent = f"projects/{PROJECT_ID}/locations/{REGION}"
full_name = f"{parent}/jobs/{SCHEDULER_JOB_ID}"

try:
    scheduler.projects().locations().jobs().create(parent=parent, body=body).execute()
    print("OK: created scheduler job.")
except Exception as e:
    err = str(e).lower()
    if "already exists" in err or "409" in err:
        print("Job exists — updating…")
        patch_body = {
            "schedule": CRON,
            "timeZone": "America/Puerto_Rico",
            "httpTarget": body["httpTarget"],
        }
        scheduler.projects().locations().jobs().patch(
            name=full_name,
            body=patch_body,
        ).execute()
        print("OK: updated scheduler job.")
    else:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

print("\nConsole:")
print(f"  https://console.cloud.google.com/cloudscheduler?project={PROJECT_ID}")
print("\nEnsure Cloud Run Job command is:")
print(f"  python sync_roster_week_job.py")
print("and the job has run.invoker for the scheduler SA (see FIX_SCHEDULER.md).")
