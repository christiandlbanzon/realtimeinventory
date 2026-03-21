"""Quick error checker - run this regularly to monitor for issues"""
import subprocess
import sys
from datetime import datetime, timedelta

def quick_check():
    """Quick status check"""
    print(f"Checking VM status at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    
    try:
        # Check cron
        cron_result = subprocess.run(
            ['gcloud', 'compute', 'ssh', 'inventory-updater-vm', '--zone=us-central1-a',
             '--command', 'crontab -l | grep vm_inventory'],
            capture_output=True, text=True, timeout=20
        )
        
        if cron_result.returncode == 0 and cron_result.stdout.strip():
            print("✅ Cron: Configured")
            if "*/5" in cron_result.stdout:
                print("✅ Schedule: Every 5 minutes")
            else:
                print("⚠️  Schedule: NOT every 5 minutes!")
        else:
            print("❌ Cron: NOT configured!")
        
        # Check errors in last hour
        error_result = subprocess.run(
            ['gcloud', 'compute', 'ssh', 'inventory-updater-vm', '--zone=us-central1-a',
             '--command', 'tail -1000 /home/banzo/inventory_cron.log | grep -i "ERROR" | tail -5'],
            capture_output=True, text=True, timeout=20
        )
        
        if error_result.returncode == 0 and error_result.stdout.strip():
            print("⚠️  Errors found in logs:")
            for line in error_result.stdout.strip().split('\n')[-5:]:
                print(f"   {line}")
        else:
            print("✅ No recent errors")
        
        # Check last run
        last_run = subprocess.run(
            ['gcloud', 'compute', 'ssh', 'inventory-updater-vm', '--zone=us-central1-a',
             '--command', 'tail -100 /home/banzo/inventory_cron.log | grep "Script completed" | tail -1'],
            capture_output=True, text=True, timeout=20
        )
        
        if last_run.returncode == 0 and last_run.stdout.strip():
            print(f"✅ Last run: {last_run.stdout.strip()}")
        else:
            print("⚠️  Could not find last run timestamp")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = quick_check()
    sys.exit(0 if success else 1)


