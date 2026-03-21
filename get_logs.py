#!/usr/bin/env python3
"""Get Cloud Run Job logs using correct API"""

import os
import sys

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
print("GETTING JOB EXECUTION LOGS")
print("="*80)

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/logging.read']
)
http = httplib2.Http(proxy_info=None, timeout=60)
authorized_http = AuthorizedHttp(credentials, http=http)
logging = build('logging', 'v2', http=authorized_http)

# Query logs for the job
print(f"\nQuerying logs for {JOB_NAME}...")
print("(This shows what the job did when it ran)\n")

log_filter = f'''
resource.type="cloud_run_job"
resource.labels.job_name="{JOB_NAME}"
resource.labels.location="{REGION}"
'''

try:
    # Use list() method correctly
    request = logging.entries().list(
        projectName=PROJECT_ID,
        filter=log_filter,
        pageSize=100,
        orderBy='timestamp desc'
    )
    
    response = request.execute()
    entries = response.get('entries', [])
    
    if entries:
        print(f"Found {len(entries)} log entries\n")
        print("="*80)
        print("RECENT LOG OUTPUT")
        print("="*80)
        print()
        
        # Show logs
        for i, entry in enumerate(entries[:50], 1):  # Show last 50 entries
            timestamp = entry.get('timestamp', '')
            severity = entry.get('severity', 'INFO')
            
            # Get message
            text_payload = entry.get('textPayload', '')
            json_payload = entry.get('jsonPayload', {})
            
            if json_payload:
                message = json_payload.get('message', '')
                if not message:
                    message = json_payload.get('textPayload', str(json_payload))
            else:
                message = text_payload
            
            if message:
                # Format timestamp
                if timestamp:
                    ts_str = timestamp[:19].replace('T', ' ')
                else:
                    ts_str = 'N/A'
                
                # Show important messages
                if any(keyword in message.lower() for keyword in ['error', 'success', 'completed', 'updated', 'sheet', 'february', 'january']):
                    print(f"[{ts_str}] [{severity}] {message}")
                elif severity in ['ERROR', 'WARNING']:
                    print(f"[{ts_str}] [{severity}] {message}")
                elif i <= 20:  # Show first 20 entries regardless
                    # Truncate long messages
                    if len(message) > 150:
                        message = message[:150] + "..."
                    print(f"[{ts_str}] {message}")
        
        print()
        print("="*80)
        print("SUMMARY")
        print("="*80)
        
        # Count by severity
        error_count = sum(1 for e in entries if e.get('severity') == 'ERROR')
        warning_count = sum(1 for e in entries if e.get('severity') == 'WARNING')
        info_count = sum(1 for e in entries if e.get('severity') == 'INFO')
        
        print(f"\nTotal log entries: {len(entries)}")
        print(f"  Errors: {error_count}")
        print(f"  Warnings: {warning_count}")
        print(f"  Info: {info_count}")
        
        if error_count == 0:
            print("\nNo errors found - job completed successfully!")
        else:
            print(f"\nWARNING: Found {error_count} error(s) - check logs above")
            
    else:
        print("No log entries found")
        print("\nThis could mean:")
        print("  1. Logs haven't been written yet (wait a minute)")
        print("  2. Logs are in a different location")
        print("  3. Need to check Cloud Logging console directly")
        
except Exception as e:
    print(f"ERROR retrieving logs: {e}")
    import traceback
    traceback.print_exc()
    print("\nYou can view logs directly in Console:")
    print(f"  https://console.cloud.google.com/logs/query?project={PROJECT_ID}")

print("\n" + "="*80)
print("VIEW LOGS IN CONSOLE")
print("="*80)
print(f"\nDirect link to logs:")
print(f"  https://console.cloud.google.com/logs/query?project={PROJECT_ID}")
print(f"\nOr filter by:")
print(f"  resource.type=\"cloud_run_job\"")
print(f"  resource.labels.job_name=\"{JOB_NAME}\"")
