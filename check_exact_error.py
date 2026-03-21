#!/usr/bin/env python3
"""Check the exact error from scheduler logs"""

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
logging_api = build('logging', 'v2', http=authorized_http)

print("="*80)
print("CHECKING EXACT SCHEDULER ERROR")
print("="*80)

# Query recent scheduler logs
filter_str = f'''
resource.type="cloud_scheduler_job"
resource.labels.job_id="{JOB_NAME}-schedule"
severity>=ERROR
timestamp>="{datetime.utcnow() - timedelta(hours=2)}"
'''

try:
    print("\nQuerying logs...")
    entries = logging_api.entries().list(
        projectIds=[PROJECT_ID],
        filter=filter_str,
        pageSize=10,
        orderBy='timestamp desc'
    ).execute()
    
    logs = entries.get('entries', [])
    
    if logs:
        print(f"\nFound {len(logs)} recent error(s):\n")
        for i, entry in enumerate(logs[:5], 1):
            timestamp = entry.get('timestamp', 'N/A')
            severity = entry.get('severity', 'N/A')
            json_payload = entry.get('jsonPayload', {})
            
            print(f"Error {i}:")
            print(f"  Time: {timestamp}")
            print(f"  Severity: {severity}")
            
            # Extract error details
            debug_info = json_payload.get('debugInfo', '')
            status = json_payload.get('status', '')
            job_name = json_payload.get('jobName', '')
            url = json_payload.get('url', '')
            
            print(f"  Status: {status}")
            print(f"  Debug Info: {debug_info}")
            if url:
                print(f"  URL: {url}")
            print()
    else:
        print("\nNo recent errors found in logs")
        print("\nTrying to get any recent scheduler entries...")
        
        # Try broader query
        filter_str2 = f'''
resource.type="cloud_scheduler_job"
resource.labels.job_id="{JOB_NAME}-schedule"
timestamp>="{datetime.utcnow() - timedelta(hours=1)}"
'''
        entries = logging_api.entries().list(
            projectIds=[PROJECT_ID],
            filter=filter_str2,
            pageSize=5,
            orderBy='timestamp desc'
        ).execute()
        
        logs2 = entries.get('entries', [])
        if logs2:
            print(f"\nFound {len(logs2)} recent log entries:")
            for entry in logs2[:3]:
                json_payload = entry.get('jsonPayload', {})
                status = json_payload.get('status', 'N/A')
                timestamp = entry.get('timestamp', 'N/A')
                print(f"  {timestamp}: {status}")
        
except Exception as e:
    print(f"ERROR accessing logs: {e}")
    print("\nCannot access logs programmatically.")
    print("Please check manually:")
    print(f"  https://console.cloud.google.com/logs/query?project={PROJECT_ID}")
    print(f"  Filter: resource.type=\"cloud_scheduler_job\"")
    print(f"          resource.labels.job_id=\"{JOB_NAME}-schedule\"")

print("\n" + "="*80)
print("ALTERNATIVE SOLUTION")
print("="*80)
print("\nIf OIDC authentication keeps failing, we can use Pub/Sub instead.")
print("This is more reliable for Cloud Run Jobs.")
print("\nShould I convert the scheduler to use Pub/Sub?")
print("="*80)
