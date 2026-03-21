#!/usr/bin/env python3
"""Debug 503 errors - check billing, quotas, and project status"""

import os
import sys

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

PROJECT_ID = "boxwood-chassis-332307"
ZONE = "us-central1-a"
SERVICE_ACCOUNT_FILE = "service-account-key.json"

print("="*80)
print("DEBUGGING 503 ERRORS")
print("="*80)
print("\nChecking possible causes:")
print("1. Billing status")
print("2. Project status")
print("3. API enablement")
print("4. Quota limits")
print("5. Service account permissions")
print("6. Regional availability")

# Authenticate
print("\n[1/6] Authenticating...")
try:
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    http = httplib2.Http(proxy_info=None)
    authorized_http = AuthorizedHttp(credentials, http=http)
    print("  OK: Authentication successful")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# Check project info
print("\n[2/6] Checking project status...")
try:
    cloudresourcemanager = build('cloudresourcemanager', 'v1', http=authorized_http)
    project = cloudresourcemanager.projects().get(projectId=PROJECT_ID).execute()
    
    project_id = project.get('projectId')
    name = project.get('name')
    project_number = project.get('projectNumber')
    lifecycle_state = project.get('lifecycleState')
    
    print(f"  Project ID: {project_id}")
    print(f"  Name: {name}")
    print(f"  Project Number: {project_number}")
    print(f"  Lifecycle State: {lifecycle_state}")
    
    if lifecycle_state != 'ACTIVE':
        print(f"  WARNING: Project is not ACTIVE! This could cause API issues.")
    else:
        print(f"  OK: Project is ACTIVE")
        
except Exception as e:
    print(f"  ERROR checking project: {e}")

# Check billing
print("\n[3/6] Checking billing status...")
try:
    cloudbilling = build('cloudbilling', 'v1', http=authorized_http)
    
    # Get billing account for project
    project_billing = cloudbilling.projects().getBillingInfo(name=f"projects/{PROJECT_ID}").execute()
    billing_account_name = project_billing.get('billingAccountName')
    billing_enabled = project_billing.get('billingEnabled', False)
    
    if billing_enabled:
        print(f"  OK: Billing is ENABLED")
        print(f"  Billing Account: {billing_account_name}")
    else:
        print(f"  WARNING: Billing is NOT ENABLED!")
        print(f"  This could cause API failures!")
        print(f"  Enable billing at: https://console.cloud.google.com/billing?project={PROJECT_ID}")
        
except Exception as e:
    error_str = str(e)
    if "403" in error_str or "permission" in error_str.lower():
        print(f"  INFO: Cannot check billing (permission issue)")
        print(f"  This is normal if service account doesn't have billing permissions")
    elif "404" in error_str:
        print(f"  WARNING: Billing account not found!")
        print(f"  Project may not have billing enabled")
    else:
        print(f"  ERROR: {e}")

# Check Compute Engine API
print("\n[4/6] Checking Compute Engine API status...")
try:
    serviceusage = build('serviceusage', 'v1', http=authorized_http)
    service_name = f"projects/{PROJECT_ID}/services/compute.googleapis.com"
    
    service = serviceusage.services().get(name=service_name).execute()
    state = service.get('state')
    
    print(f"  State: {state}")
    if state == 'ENABLED':
        print(f"  OK: Compute Engine API is ENABLED")
    elif state == 'DISABLED':
        print(f"  ERROR: Compute Engine API is DISABLED!")
        print(f"  Enable it at: https://console.cloud.google.com/apis/api/compute.googleapis.com/overview?project={PROJECT_ID}")
    else:
        print(f"  INFO: API state is {state}")
        
except Exception as e:
    error_str = str(e)
    if "403" in error_str:
        print(f"  INFO: Cannot check API status (permission issue)")
    else:
        print(f"  ERROR: {e}")

# Check quotas
print("\n[5/6] Checking Compute Engine quotas...")
try:
    compute = build('compute', 'v1', http=authorized_http)
    
    # Check if we can list instances (tests basic API access)
    try:
        instances = compute.instances().list(project=PROJECT_ID, zone=ZONE, maxResults=1).execute()
        print(f"  OK: Can list instances (API is accessible)")
    except Exception as e:
        error_str = str(e)
        if "503" in error_str:
            print(f"  ERROR: Getting 503 when listing instances")
            print(f"  This confirms the API service is down")
        else:
            print(f"  ERROR: {e}")
    
    # Try to get quota info
    try:
        # Check regional quotas
        region = ZONE.rsplit('-', 1)[0]  # us-central1 from us-central1-a
        quotas = compute.regions().get(project=PROJECT_ID, region=region).execute()
        
        quotas_list = quotas.get('quotas', [])
        print(f"  Checking quotas in region {region}...")
        
        for quota in quotas_list:
            metric = quota.get('metric', '')
            limit = quota.get('limit', 0)
            usage = quota.get('usage', 0)
            
            # Check important quotas
            if 'INSTANCES' in metric or 'CPUS' in metric:
                print(f"    {metric}: {usage}/{limit}")
                if usage >= limit * 0.9:  # 90% threshold
                    print(f"      WARNING: Quota nearly exhausted!")
                    
    except Exception as e:
        error_str = str(e)
        if "503" in error_str:
            print(f"  ERROR: Getting 503 when checking quotas")
        elif "403" in error_str:
            print(f"  INFO: Cannot check quotas (permission issue)")
        else:
            print(f"  INFO: {e}")
            
except Exception as e:
    print(f"  ERROR: {e}")

# Check zone availability
print("\n[6/6] Checking zone availability...")
try:
    compute = build('compute', 'v1', http=authorized_http)
    zone_info = compute.zones().get(project=PROJECT_ID, zone=ZONE).execute()
    
    status = zone_info.get('status')
    print(f"  Zone: {ZONE}")
    print(f"  Status: {status}")
    
    if status == 'UP':
        print(f"  OK: Zone is UP")
    elif status == 'DOWN':
        print(f"  ERROR: Zone is DOWN!")
        print(f"  Try a different zone")
    else:
        print(f"  INFO: Zone status is {status}")
        
except Exception as e:
    error_str = str(e)
    if "503" in error_str:
        print(f"  ERROR: Getting 503 when checking zone")
        print(f"  This confirms API service is unavailable")
    else:
        print(f"  ERROR: {e}")

print("\n" + "="*80)
print("DIAGNOSIS SUMMARY")
print("="*80)
print("\nIf billing is disabled or API is disabled, that's likely the issue.")
print("If everything shows OK but still getting 503, it's a Google Cloud service outage.")
print("\nCheck Google Cloud Status: https://status.cloud.google.com/")
print(f"Check your project: https://console.cloud.google.com/home/dashboard?project={PROJECT_ID}")
