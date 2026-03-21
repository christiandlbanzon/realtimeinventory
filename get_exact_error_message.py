#!/usr/bin/env python3
"""Get the EXACT error message - no more guessing"""

import os
import sys

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'service-account-key.json'

print("="*80)
print("WE NEED THE EXACT ERROR MESSAGE")
print("="*80)
print("\nThe roles are correct, but it's still failing.")
print("We need to see the ACTUAL error from Cloud Scheduler logs.")
print()

print("PLEASE DO THIS:")
print("="*80)
print("\n1. Go to Cloud Scheduler:")
print("   https://console.cloud.google.com/cloudscheduler?project=boxwood-chassis-332307")
print("\n2. Click on 'inventory-updater-schedule'")
print("\n3. Look for one of these:")
print("   - 'VIEW LOGS' button (click it)")
print("   - 'Execution history' section")
print("   - Click on the most recent FAILED execution")
print("\n4. In the logs, look for:")
print("   - Error messages")
print("   - Status codes")
print("   - Debug info")
print("\n5. Copy the EXACT error text you see")
print("   Examples:")
print("   - 'UNAUTHENTICATED'")
print("   - 'PERMISSION_DENIED'")
print("   - 'HTTP 401'")
print("   - 'HTTP 403'")
print("   - Any error message text")
print("\n6. Paste that error message here")
print("\n" + "="*80)
print("\nWITHOUT the exact error message, we're just guessing.")
print("Once you share it, I can fix it immediately.")
print("="*80)
