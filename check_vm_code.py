#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check the actual code on VM to see how quantity is handled
"""

import subprocess
import os
import tempfile
import shutil
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

VM_NAME = "inventory-updater-vm"
VM_ZONE = "us-central1-a"
SCRIPT_PATH = "/home/banzo/vm_inventory_updater.py"

# Find gcloud path
GCLOUD_PATH = r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
if not os.path.exists(GCLOUD_PATH):
    GCLOUD_PATH = 'gcloud'

def get_env():
    env = os.environ.copy()
    temp_config = tempfile.mkdtemp()
    env['CLOUDSDK_CONFIG'] = temp_config
    env['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath('service-account-key.json')
    for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
        env.pop(proxy_var, None)
    return env, temp_config

print("="*80)
print("CHECKING VM CODE FOR QUANTITY HANDLING")
print("="*80)
print()

env, temp_config = get_env()

# Check if file exists
print("[1] Checking if script exists on VM...")
result = subprocess.run(
    [GCLOUD_PATH, 'compute', 'ssh', VM_NAME,
     '--zone', VM_ZONE,
     '--command', f'test -f {SCRIPT_PATH} && echo "EXISTS" || echo "NOT_FOUND"'],
    env=env,
    capture_output=True,
    text=True,
    timeout=30
)

if 'NOT_FOUND' in result.stdout:
    print(f"❌ Script not found at {SCRIPT_PATH}")
    print("   Trying to find the script...")
    
    # Try to find Python files
    result = subprocess.run(
        [GCLOUD_PATH, 'compute', 'ssh', VM_NAME,
         '--zone', VM_ZONE,
         '--command', 'ls -la /home/banzo/*.py'],
        env=env,
        capture_output=True,
        text=True,
        timeout=30
    )
    print(result.stdout)
else:
    print(f"✅ Script exists at {SCRIPT_PATH}")
    
    # Get file size
    print("\n[2] Getting file info...")
    result = subprocess.run(
        [GCLOUD_PATH, 'compute', 'ssh', VM_NAME,
         '--zone', VM_ZONE,
         '--command', f'ls -lh {SCRIPT_PATH}'],
        env=env,
        capture_output=True,
        text=True,
        timeout=30
    )
    print(result.stdout)
    
    # Search for quantity handling code
    print("\n[3] Searching for quantity handling code...")
    searches = [
        ("quantity =", "Lines with 'quantity ='"),
        ("quantity = 1", "Lines with 'quantity = 1'"),
        ("quantity = item.get", "Lines reading quantity from item"),
        ("cookie_sales", "Lines updating cookie_sales"),
        ("fetch_clover_sales", "Function fetch_clover_sales"),
    ]
    
    for pattern, description in searches:
        print(f"\n  {description}:")
        result = subprocess.run(
            [GCLOUD_PATH, 'compute', 'ssh', VM_NAME,
             '--zone', VM_ZONE,
             '--command', f'grep -n "{pattern}" {SCRIPT_PATH} | head -10'],
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.stdout.strip():
            for line in result.stdout.strip().split('\n')[:10]:
                print(f"    {line}")
        else:
            print(f"    (not found)")
    
    # Get the specific section around quantity handling
    print("\n[4] Getting code around quantity handling (lines 850-980)...")
    result = subprocess.run(
        [GCLOUD_PATH, 'compute', 'ssh', VM_NAME,
         '--zone', VM_ZONE,
         '--command', f'sed -n "850,980p" {SCRIPT_PATH}'],
        env=env,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.stdout.strip():
        print("\n  Code snippet:")
        print("-" * 80)
        for i, line in enumerate(result.stdout.strip().split('\n'), start=850):
            if 'quantity' in line.lower() or 'cookie_sales' in line.lower():
                print(f"  {i:4d}: {line}")
        print("-" * 80)
    else:
        print("  Could not retrieve code (file might be empty or different)")

# Cleanup
try:
    shutil.rmtree(temp_config, ignore_errors=True)
except:
    pass

print("\n" + "="*80)
print("CHECK COMPLETE")
print("="*80)
