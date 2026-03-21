#!/usr/bin/env python3
"""Try to grant permission - user needs to authenticate first"""

import os
import sys

print("="*80)
print("GRANTING PERMISSION ON CLOUD RUN JOB")
print("="*80)
print("\ngcloud has permission issues, so we need to use the Console.")
print("\nBUT - let me try using Python API with user credentials...")
print()

# Try to use application default credentials (user)
os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)

try:
    from google.auth import default
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2
    
    print("Attempting to use Application Default Credentials (your user account)...")
    credentials, project = default()
    
    http = httplib2.Http(proxy_info=None, timeout=60)
    authorized_http = AuthorizedHttp(credentials, http=http)
    run = build('run', 'v2', http=authorized_http)
    
    PROJECT_ID = "boxwood-chassis-332307"
    REGION = "us-east1"
    JOB_NAME = "inventory-updater"
    SA_EMAIL = "scheduler-invoker@boxwood-chassis-332307.iam.gserviceaccount.com"
    
    job_name = f'projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}'
    member = f'serviceAccount:{SA_EMAIL}'
    role = 'roles/run.invoker'
    
    print("\n[1/3] Getting current IAM policy...")
    policy = run.projects().locations().jobs().getIamPolicy(resource=job_name).execute()
    
    bindings = policy.get('bindings', [])
    print(f"  Current bindings: {len(bindings)}")
    
    # Check if already exists
    for binding in bindings:
        if binding.get('role') == role:
            members = binding.get('members', [])
            if member in members:
                print(f"  OK: {SA_EMAIL} already has {role}")
                print("  Permission already granted!")
                sys.exit(0)
    
    print("\n[2/3] Adding service account...")
    invoker_binding = None
    for binding in bindings:
        if binding.get('role') == role:
            invoker_binding = binding
            break
    
    if invoker_binding:
        invoker_binding['members'].append(member)
    else:
        invoker_binding = {'role': role, 'members': [member]}
        bindings.append(invoker_binding)
    
    print("\n[3/3] Setting IAM policy...")
    updated_policy = {
        'bindings': bindings,
        'etag': policy.get('etag')
    }
    
    result = run.projects().locations().jobs().setIamPolicy(
        resource=job_name,
        body={'policy': updated_policy}
    ).execute()
    
    print(f"\n  SUCCESS!")
    print(f"  Granted {role} to {SA_EMAIL}")
    print(f"  Total bindings: {len(result.get('bindings', []))}")
    
    print("\n" + "="*80)
    print("PERMISSION GRANTED!")
    print("="*80)
    print("\nWait 2-3 minutes, then manually trigger scheduler.")
    print("="*80)
    
except Exception as e:
    error_str = str(e)
    if 'default' in error_str.lower() or 'credentials' in error_str.lower():
        print("ERROR: No user credentials found")
        print("\n" + "="*80)
        print("USE THE CONSOLE INSTEAD")
        print("="*80)
        print("\nSince gcloud has permission issues, use the Console:")
        print("\n1. Go to:")
        print("   https://console.cloud.google.com/run/jobs?project=boxwood-chassis-332307")
        print("\n2. Click on 'inventory-updater'")
        print("\n3. Look for 'PERMISSIONS' tab or button")
        print("   (It might be in a menu, or at the top)")
        print("\n4. Click '+ GRANT ACCESS' or 'ADD PRINCIPAL'")
        print("\n5. Add:")
        print(f"   Principal: scheduler-invoker@boxwood-chassis-332307.iam.gserviceaccount.com")
        print(f"   Role: Cloud Run Invoker")
        print("\n6. Click 'SAVE'")
        print("\n7. Wait 2-3 minutes")
        print("\n8. Manually trigger scheduler - it should work!")
        print("="*80)
    else:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
