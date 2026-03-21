#!/usr/bin/env python3
"""
Check what files are actually on the VM
"""

import os
import sys
import subprocess

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

PROJECT_ID = "boxwood-chassis-332307"
ZONE = "us-central1-a"
VM_NAME = "real-time-inventory"

def check_vm_files():
    """Check files on VM using gcloud compute ssh"""
    print("="*80)
    print("CHECKING FILES ON VM")
    print("="*80)
    
    commands = [
        "ls -lh /home/banzo/*.py /home/banzo/*.json 2>/dev/null || echo 'No files found'",
        "crontab -l 2>/dev/null || echo 'No cron jobs'",
        "ps aux | grep vm_inventory_updater | grep -v grep || echo 'Process not running'"
    ]
    
    for i, cmd in enumerate(commands, 1):
        print(f"\n[{i}/{len(commands)}] Running: {cmd}")
        try:
            result = subprocess.run(
                [
                    'gcloud', 'compute', 'ssh', VM_NAME,
                    '--zone', ZONE,
                    '--project', PROJECT_ID,
                    '--command', cmd
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"✅ Output:\n{result.stdout}")
            else:
                print(f"⚠️  Error:\n{result.stderr}")
                
        except Exception as e:
            print(f"❌ Failed: {e}")

if __name__ == "__main__":
    check_vm_files()
