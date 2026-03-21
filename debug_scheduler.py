#!/usr/bin/env python3
"""Debug why scheduler isn't running the job"""

import os
import sys
from datetime import datetime

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'service-account-key.json'

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

PROJECT_ID = "boxwood-chassis-332307"
REGION = "us-east1"
JOB_NAME = "inventory-updater"

print("="*80)
print("DEBUGGING SCHEDULER ISSUE")
print("="*80)

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
scheduler = build('cloudscheduler', 'v1', http=authorized_http)
run = build('run', 'v2', http=authorized_http)

# Check scheduler details
print("\n[1/3] Checking Cloud Scheduler configuration...")
scheduler_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}-schedule'

try:
    scheduler_job = scheduler.projects().locations().jobs().get(
        name=scheduler_name
    ).execute()
    
    print(f"  Name: {scheduler_job.get('name')}")
    print(f"  Schedule: {scheduler_job.get('schedule')}")
    print(f"  State: {scheduler_job.get('state')}")
    print(f"  Timezone: {scheduler_job.get('timeZone', 'UTC')}")
    
    # Check HTTP target
    http_target = scheduler_job.get('httpTarget', {})
    print(f"\n  HTTP Target:")
    print(f"    URI: {http_target.get('uri')}")
    print(f"    Method: {http_target.get('httpMethod')}")
    
    oidc_token = http_target.get('oidcToken', {})
    print(f"    Service Account: {oidc_token.get('serviceAccountEmail')}")
    
    # Check status
    status = scheduler_job.get('status', {})
    print(f"\n  Status:")
    print(f"    Last attempt time: {status.get('lastAttemptTime', 'Never')}")
    print(f"    Next run time: {status.get('scheduleTime', 'Not scheduled')}")
    
    # Check for errors
    last_attempt = status.get('lastAttemptTime')
    if not last_attempt:
        print(f"\n  WARNING: Scheduler has never attempted to run!")
        print(f"  This could mean:")
        print(f"    1. It's waiting for the next scheduled time")
        print(f"    2. There's a configuration issue")
        print(f"    3. Permissions issue")
    
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Check Cloud Run Job
print("\n[2/3] Checking Cloud Run Job...")
job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'

try:
    job = run.projects().locations().jobs().get(
        name=job_name
    ).execute()
    
    print(f"  Name: {job.get('name')}")
    print(f"  State: {job.get('state', 'ACTIVE')}")
    print(f"  UID: {job.get('uid')}")
    
    # Check template
    template = job.get('template', {}).get('template', {})
    containers = template.get('containers', [])
    if containers:
        print(f"  Image: {containers[0].get('image')}")
    print(f"  Service Account: {template.get('serviceAccount')}")
    print(f"  Max Retries: {template.get('maxRetries')}")
    print(f"  Timeout: {template.get('timeout')}")
    
    # List executions
    print(f"\n  Executions:")
    try:
        executions = run.projects().locations().jobs().executions().list(
            parent=job_name,
            pageSize=10
        ).execute()
        
        exec_list = executions.get('executions', [])
        if exec_list:
            for i, exec_item in enumerate(exec_list[:5], 1):
                exec_name = exec_item.get('name', 'N/A')
                create_time = exec_item.get('createTime', 'N/A')
                conditions = exec_item.get('status', {}).get('conditions', [])
                if conditions:
                    condition_type = conditions[0].get('type', 'Unknown')
                    reason = conditions[0].get('reason', '')
                    message = conditions[0].get('message', '')
                    print(f"    {i}. {condition_type} at {create_time}")
                    if reason:
                        print(f"       Reason: {reason}")
                    if message:
                        print(f"       Message: {message}")
                else:
                    print(f"    {i}. Status unknown at {create_time}")
        else:
            print("    - No executions found")
            print("    - Job has never been triggered")
            
    except Exception as e:
        print(f"    ERROR listing executions: {e}")
        
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Check if scheduler can access the job
print("\n[3/3] Checking scheduler permissions...")
print("  Verifying scheduler can invoke Cloud Run Job...")

# The scheduler uses OIDC token with service account
# Let's verify the service account has the right permissions
sa_email = '703996360436-compute@developer.gserviceaccount.com'
print(f"  Service Account: {sa_email}")
print(f"  This service account needs 'run.invoker' role on the Cloud Run Job")

print("\n" + "="*80)
print("DIAGNOSIS")
print("="*80)
print("\nIf scheduler shows 'ENABLED' but hasn't run:")
print("  1. Check if enough time has passed (runs every 5 minutes)")
print("  2. Verify service account has 'Cloud Run Invoker' role")
print("  3. Check scheduler logs in Cloud Logging")
print("\nTo fix permissions, run:")
print(f"  gcloud run jobs add-iam-policy-binding {JOB_NAME} \\")
print(f"    --region={REGION} \\")
print(f"    --member=serviceAccount:{sa_email} \\")
print(f"    --role=roles/run.invoker")
