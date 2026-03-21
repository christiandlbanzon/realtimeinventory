"""Check VM logs for column detection issues"""
import subprocess
import sys

def check_vm_logs():
    """Check the VM logs for column detection issues"""
    print("="*80)
    print("CHECKING VM LOGS FOR COLUMN DETECTION ISSUES")
    print("="*80)
    
    print("\n[1/3] Checking recent log entries...")
    print("Looking for column detection messages...")
    print("\nTo check VM logs manually, run:")
    print("  gcloud compute ssh inventory-updater-vm --command='tail -100 /home/banzo/inventory_cron.log'")
    print("\nOr check for column detection:")
    print("  gcloud compute ssh inventory-updater-vm --command='grep -i \"location columns found\" /home/banzo/inventory_cron.log | tail -20'")
    
    print("\n[2/3] Checking for errors...")
    print("Run this to see recent errors:")
    print("  gcloud compute ssh inventory-updater-vm --command='grep -i error /home/banzo/inventory_cron.log | tail -20'")
    
    print("\n[3/3] Checking if script is running...")
    print("Run this to see if the cron job is active:")
    print("  gcloud compute ssh inventory-updater-vm --command='crontab -l | grep vm_inventory'")
    
    print("\n" + "="*80)
    print("KEY LOG MESSAGES TO LOOK FOR:")
    print("="*80)
    print("GOOD: 'Found Live Sales Data (Do Not Touch) column for [Location]'")
    print("GOOD: 'Location columns found: {...}' with all 6 locations")
    print("BAD: 'Location columns found: {}' (empty)")
    print("BAD: 'No updates to make' (no columns detected)")
    print("BAD: 'ERROR: Could not find Live Sales Data column'")
    
    print("\n" + "="*80)
    print("AUTOMATED CHECK:")
    print("="*80)
    
    try:
        # Try to SSH into VM and check logs
        print("\nAttempting to check VM logs...")
        
        # Check recent column detection messages
        result = subprocess.run(
            ['gcloud', 'compute', 'ssh', 'inventory-updater-vm', 
             '--command', 'grep -i "location columns found" /home/banzo/inventory_cron.log | tail -10'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout.strip():
            print("\n📋 Recent column detection messages:")
            print(result.stdout)
        else:
            print("⚠️  Could not retrieve logs automatically")
            print("   Error:", result.stderr if result.stderr else "No output")
            print("\n   Please run manually:")
            print("   gcloud compute ssh inventory-updater-vm --command='tail -200 /home/banzo/inventory_cron.log'")
        
        # Check for errors
        print("\n" + "-"*80)
        print("Checking for errors...")
        result2 = subprocess.run(
            ['gcloud', 'compute', 'ssh', 'inventory-updater-vm', 
             '--command', 'grep -i "error\\|warning" /home/banzo/inventory_cron.log | tail -20'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result2.returncode == 0 and result2.stdout.strip():
            print("\n⚠️  Recent errors/warnings:")
            print(result2.stdout)
        else:
            print("✅ No recent errors found (or log file doesn't exist)")
        
        # Check last run summary
        print("\n" + "-"*80)
        print("Checking last script run...")
        result3 = subprocess.run(
            ['gcloud', 'compute', 'ssh', 'inventory-updater-vm', 
             '--command', 'tail -50 /home/banzo/inventory_cron.log | grep -A 5 "Location columns found"'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result3.returncode == 0 and result3.stdout.strip():
            print("\n📊 Last column detection result:")
            print(result3.stdout)
        else:
            print("⚠️  Could not find recent column detection messages")
            print("   This might mean:")
            print("   1. Script hasn't run recently")
            print("   2. Column detection is failing silently")
            print("   3. Log file is in a different location")
        
    except subprocess.TimeoutExpired:
        print("⏱️  Connection timeout - VM might be unreachable")
    except FileNotFoundError:
        print("❌ gcloud CLI not found. Please install Google Cloud SDK")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nPlease check VM logs manually using:")
        print("  gcloud compute ssh inventory-updater-vm --command='tail -200 /home/banzo/inventory_cron.log'")

if __name__ == "__main__":
    check_vm_logs()

