#!/usr/bin/env python3
"""
Setup script to configure automated inventory updates on GCP VM
This script will:
1. Set up cron job to run every 5 minutes
2. Create proper environment variables
3. Set up logging
"""

import subprocess
import os

def setup_cron_job():
    """Set up cron job to run every 5 minutes"""
    
    # Get current working directory
    cwd = "/home/banzo"
    
    # Create cron job entry
    cron_entry = f"*/5 * * * * cd {cwd} && /home/banzo/venv/bin/python vm_inventory_updater.py >> inventory_cron.log 2>&1"
    
    # Add to crontab
    try:
        # Create temporary crontab file
        subprocess.run(f"echo '{cron_entry}' > /tmp/new_crontab", shell=True, check=True)
        
        # Get existing crontab (if any)
        result = subprocess.run("crontab -l 2>/dev/null || echo ''", shell=True, capture_output=True, text=True)
        existing_cron = result.stdout
        
        # Check if our job already exists
        if "vm_inventory_updater.py" not in existing_cron:
            # Combine existing crontab with new entry
            with open("/tmp/new_crontab", "w") as f:
                if existing_cron.strip():
                    f.write(existing_cron)
                    f.write("\n")
                f.write(cron_entry)
                f.write("\n")
            
            # Install new crontab
            subprocess.run("crontab /tmp/new_crontab", shell=True, check=True)
            print("✅ Cron job added successfully!")
            print(f"   Schedule: Every 5 minutes")
            print(f"   Command: cd {cwd} && /home/banzo/venv/bin/python vm_inventory_updater.py")
        else:
            print("ℹ️  Cron job already exists")
        
        # Clean up
        subprocess.run("rm -f /tmp/new_crontab", shell=True)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error setting up cron job: {e}")
        return False
    
    return True

def check_python_environment():
    """Check if Python virtual environment is set up"""
    venv_path = "/home/banzo/venv/bin/python"
    
    if os.path.exists(venv_path):
        print("✅ Virtual environment found")
        
        # Check if required packages are installed
        try:
            result = subprocess.run(f"{venv_path} -c 'import google.auth, requests, fuzzywuzzy'", 
                                  shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Required packages are installed")
                return True
            else:
                print("⚠️  Some packages may be missing")
                print("   Run: /home/banzo/venv/bin/pip install -r requirements.txt")
                return False
        except Exception as e:
            print(f"❌ Error checking packages: {e}")
            return False
    else:
        print("❌ Virtual environment not found")
        print("   Run: python3 -m venv /home/banzo/venv")
        print("   Then: /home/banzo/venv/bin/pip install -r requirements.txt")
        return False

def create_requirements_file():
    """Create requirements.txt if it doesn't exist"""
    requirements = """google-auth==2.23.4
google-auth-oauthlib==1.1.0
google-auth-httplib2==0.1.1
google-api-python-client==2.108.0
requests==2.31.0
fuzzywuzzy==0.18.0
python-levenshtein==0.21.1
"""
    
    with open("/home/banzo/requirements.txt", "w") as f:
        f.write(requirements)
    print("✅ requirements.txt created")

def show_status():
    """Show current cron jobs and system status"""
    print("\n📋 CURRENT STATUS:")
    
    # Show crontab
    try:
        result = subprocess.run("crontab -l", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("📅 Current cron jobs:")
            for line in result.stdout.strip().split('\n'):
                if line.strip() and not line.startswith('#'):
                    print(f"   {line}")
        else:
            print("   No cron jobs found")
    except Exception as e:
        print(f"❌ Error reading crontab: {e}")
    
    # Check if script exists
    script_path = "/home/banzo/vm_inventory_updater.py"
    if os.path.exists(script_path):
        print("✅ Main script found")
    else:
        print("❌ Main script not found")
    
    # Check credentials
    creds_path = "/home/banzo/clover_creds.json"
    if os.path.exists(creds_path):
        print("✅ Clover credentials found")
    else:
        print("❌ Clover credentials not found")
    
    service_account_path = "/home/banzo/service-account-key.json"
    if os.path.exists(service_account_path):
        print("✅ Service account key found")
    else:
        print("❌ Service account key not found")

def main():
    print("🚀 Setting up automated inventory updates on GCP VM...")
    print("=" * 60)
    
    # Check environment
    if not check_python_environment():
        print("\n⚠️  Please set up the Python environment first:")
        print("   python3 -m venv /home/banzo/venv")
        print("   /home/banzo/venv/bin/pip install -r requirements.txt")
        return
    
    # Create requirements file
    create_requirements_file()
    
    # Set up cron job
    if setup_cron_job():
        print("\n🎉 Setup complete!")
        print("\nThe inventory updater will now run every 5 minutes automatically.")
        print("Check logs with: tail -f /home/banzo/inventory_cron.log")
    
    # Show status
    show_status()

if __name__ == "__main__":
    main()


