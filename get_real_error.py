#!/usr/bin/env python3
"""Get the ACTUAL error from scheduler logs - no guessing"""

import os
import sys
from datetime import datetime, timedelta

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'service-account-key.json'

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2
import json

PROJECT_ID = "boxwood-chassis-332307"
REGION = "us-east1"
JOB_NAME = "inventory-updater"

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/logging.read']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)

# Use Logging API v2
from google.cloud import logging as cloud_logging

print("="*80)
print("GETTING ACTUAL ERROR FROM LOGS")
print("="*80)
print("\nNo more guessing - let's see the REAL error message.")
print()

try:
    client = cloud_logging.Client(project=PROJECT_ID, credentials=credentials)
    
    # Query for scheduler errors
    filter_str = f'''
resource.type="cloud_scheduler_job"
resource.labels.job_id="{JOB_NAME}-schedule"
severity>=ERROR
timestamp>="{datetime.now().replace(tzinfo=None) - timedelta(hours=1)}"
'''
    
    print("Querying logs for errors...")
    entries = client.list_entries(
        filter_=filter_str,
        order_by=cloud_logging.DESCENDING,
        page_size=5
    )
    
    error_found = False
    for entry in entries:
        error_found = True
        print("\n" + "="*80)
        print("ERROR FOUND:")
        print("="*80)
        print(f"\nTimestamp: {entry.timestamp}")
        print(f"Severity: {entry.severity}")
        print(f"Log Name: {entry.log_name}")
        
        payload = entry.payload
        if isinstance(payload, dict):
            print(f"\nPayload:")
            print(json.dumps(payload, indent=2))
            
            # Extract key error info
            debug_info = payload.get('debugInfo', '')
            status = payload.get('status', '')
            job_name = payload.get('jobName', '')
            url = payload.get('url', '')
            
            print(f"\nKey Details:")
            print(f"  Status: {status}")
            print(f"  Debug Info: {debug_info}")
            if url:
                print(f"  URL: {url}")
        else:
            print(f"\nPayload: {payload}")
        
        print("\n" + "="*80)
        break  # Just show the most recent error
    
    if not error_found:
        print("\nNo recent errors found in logs.")
        print("Trying broader query...")
        
        # Try without severity filter
        filter_str2 = f'''
resource.type="cloud_scheduler_job"
resource.labels.job_id="{JOB_NAME}-schedule"
timestamp>="{datetime.now().replace(tzinfo=None) - timedelta(minutes=10)}"
'''
        
        entries = client.list_entries(
            filter_=filter_str2,
            order_by=cloud_logging.DESCENDING,
            page_size=3
        )
        
        for entry in entries:
            payload = entry.payload
            if isinstance(payload, dict):
                status = payload.get('status', '')
                if status in ['FAILED', 'UNAUTHENTICATED', 'PERMISSION_DENIED']:
                    print(f"\nFound {status} entry:")
                    print(json.dumps(payload, indent=2))
                    break
        
except ImportError:
    print("ERROR: google-cloud-logging not installed")
    print("Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-cloud-logging", "-q"])
    
    # Retry
    from google.cloud import logging as cloud_logging
    client = cloud_logging.Client(project=PROJECT_ID, credentials=credentials)
    
    filter_str = f'''
resource.type="cloud_scheduler_job"
resource.labels.job_id="{JOB_NAME}-schedule"
severity>=ERROR
'''
    
    entries = client.list_entries(
        filter_=filter_str,
        order_by=cloud_logging.DESCENDING,
        page_size=3
    )
    
    for entry in entries:
        print(f"\n{entry.timestamp}: {entry.severity}")
        print(json.dumps(entry.payload if isinstance(entry.payload, dict) else str(entry.payload), indent=2))
        break

except Exception as e:
    print(f"ERROR accessing logs: {e}")
    import traceback
    traceback.print_exc()
    
    print("\n" + "="*80)
    print("ALTERNATIVE: Check logs manually")
    print("="*80)
    print("\nGo to:")
    print(f"  https://console.cloud.google.com/logs/query?project={PROJECT_ID}")
    print("\nPaste this query:")
    print(f'resource.type="cloud_scheduler_job"')
    print(f'resource.labels.job_id="{JOB_NAME}-schedule"')
    print(f'severity>=ERROR')
    print("\nLook for the most recent error and copy the exact error message.")
    print("="*80)

print("\n" + "="*80)
print("NEXT: Once we have the exact error, we can fix it properly.")
print("="*80)
