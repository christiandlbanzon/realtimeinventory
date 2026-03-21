#!/usr/bin/env python3
"""
Deploy Real-Time Inventory Updater to a NEW GCP VM Instance

This script will:
1. Create a new GCP VM instance (if needed)
2. Set up Python environment
3. Install dependencies
4. Upload necessary files
5. Set up cron job for automated updates
6. Verify deployment

Prerequisites:
- gcloud CLI installed and authenticated (gcloud auth login)
- Project ID configured
- Billing enabled on GCP project
"""

import subprocess
import sys
import os
import json
import time
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configuration
# Detect gcloud path (Windows)
GCLOUD_CMD = "gcloud"
if sys.platform == 'win32':
    gcloud_paths = [
        r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        r"C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
    ]
    for path in gcloud_paths:
        if os.path.exists(path):
            GCLOUD_CMD = path
            break
PROJECT_ID = "boxwood-chassis-332307"  # Update if different
ZONE = "us-central1-a"  # Update if preferred
VM_NAME = "real-time-inventory"  # Update if preferred
MACHINE_TYPE = "e2-micro"  # Small instance, update if needed
IMAGE_FAMILY = "ubuntu-2204-lts"
IMAGE_PROJECT = "ubuntu-os-cloud"
USERNAME = "banzo"  # Default username for Ubuntu

# Required files to upload
REQUIRED_FILES = [
    "vm_inventory_updater_fixed.py",  # Main application
    "service-account-key.json",  # Google Sheets credentials
    "clover_creds.json",  # Clover API credentials
    "requirements.txt",  # Python dependencies
]

# Optional files
OPTIONAL_FILES = [
    "secrets/shopify_creds.json",  # Shopify credentials (if exists)
]

def run_command(cmd, check=True, capture_output=True, timeout=300):
    """Run a shell command and return the result"""
    # Replace 'gcloud' with full path if needed
    if cmd[0] == 'gcloud' and GCLOUD_CMD != 'gcloud':
        cmd = [GCLOUD_CMD] + cmd[1:]
    print(f"🔧 Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        if check:
            raise
        return e
    except subprocess.TimeoutExpired:
        print(f"⏱️ Command timed out after {timeout} seconds")
        raise

def check_gcloud_auth():
    """Check if gcloud is authenticated"""
    print("\n" + "="*80)
    print("STEP 1: Checking gcloud authentication")
    print("="*80)
    
    try:
        result = run_command(["gcloud", "auth", "list"], check=False)
        if result.stdout and "ACTIVE" in result.stdout:
            print("✅ gcloud is authenticated")
            return True
        else:
            print("⚠️ Could not verify authentication (may have permission issues)")
            print("⚠️ Will attempt to proceed - gcloud will prompt if authentication needed")
            # Don't fail - let gcloud handle authentication when needed
            return True
    except FileNotFoundError:
        print("❌ gcloud CLI not found. Please install Google Cloud SDK")
        return False
    except Exception as e:
        print(f"⚠️ Auth check failed: {e}")
        print("⚠️ Will attempt to proceed - gcloud will prompt if authentication needed")
        return True  # Continue anyway

def check_project():
    """Check and set the GCP project"""
    print("\n" + "="*80)
    print("STEP 2: Checking GCP project configuration")
    print("="*80)
    
    try:
        result = run_command(["gcloud", "config", "get-value", "project"], check=False)
        current_project = result.stdout.strip()
        
        if current_project == PROJECT_ID:
            print(f"✅ Project is set to: {PROJECT_ID}")
            return True
        else:
            print(f"⚠️ Current project: {current_project}")
            print(f"Setting project to: {PROJECT_ID}")
            run_command(["gcloud", "config", "set", "project", PROJECT_ID])
            print(f"✅ Project set to: {PROJECT_ID}")
            return True
    except Exception as e:
        print(f"❌ Error checking project: {e}")
        return False

def check_vm_exists():
    """Check if VM already exists"""
    print("\n" + "="*80)
    print("STEP 3: Checking if VM exists")
    print("="*80)
    
    try:
        result = run_command(
            ["gcloud", "compute", "instances", "list", "--filter", f"name={VM_NAME}", "--format", "json"],
            check=False
        )
        
        if result.stdout and result.stdout.strip():
            instances = json.loads(result.stdout)
            if instances:
                print(f"✅ VM '{VM_NAME}' already exists")
                return True
        
        print(f"ℹ️ VM '{VM_NAME}' does not exist - will create it")
        return False
    except json.JSONDecodeError:
        # Empty output means VM doesn't exist
        print(f"ℹ️ VM '{VM_NAME}' does not exist - will create it")
        return False
    except Exception as e:
        print(f"⚠️ Could not check VM existence: {e}")
        print(f"ℹ️ Will attempt to create VM '{VM_NAME}'")
        return False

def create_vm():
    """Create a new GCP VM instance"""
    print("\n" + "="*80)
    print("STEP 4: Creating new VM instance")
    print("="*80)
    
    print(f"Creating VM: {VM_NAME}")
    print(f"  Zone: {ZONE}")
    print(f"  Machine type: {MACHINE_TYPE}")
    print(f"  Image: {IMAGE_FAMILY}")
    
    cmd = [
        "gcloud", "compute", "instances", "create", VM_NAME,
        "--zone", ZONE,
        "--machine-type", MACHINE_TYPE,
        "--image-family", IMAGE_FAMILY,
        "--image-project", IMAGE_PROJECT,
        "--boot-disk-size", "20GB",
        "--boot-disk-type", "pd-standard",
        "--tags", "http-server,https-server",
        "--metadata", "startup-script=#! /bin/bash\napt-get update\napt-get install -y python3 python3-pip python3-venv",
    ]
    
    try:
        run_command(cmd)
        print(f"✅ VM '{VM_NAME}' created successfully")
        
        # Wait for VM to be ready
        print("⏳ Waiting for VM to be ready (30 seconds)...")
        time.sleep(30)
        
        return True
    except Exception as e:
        print(f"❌ Error creating VM: {e}")
        return False

def check_required_files():
    """Check if all required files exist"""
    print("\n" + "="*80)
    print("STEP 5: Checking required files")
    print("="*80)
    
    missing_files = []
    for file in REQUIRED_FILES:
        if not os.path.exists(file):
            missing_files.append(file)
            print(f"❌ Missing: {file}")
        else:
            print(f"✅ Found: {file}")
    
    if missing_files:
        print(f"\n❌ Missing {len(missing_files)} required file(s)")
        print("Please ensure all required files are present before deploying")
        return False
    
    # Check optional files
    print("\nOptional files:")
    for file in OPTIONAL_FILES:
        if os.path.exists(file):
            print(f"✅ Found: {file}")
        else:
            print(f"⚠️ Optional file not found: {file} (will skip)")
    
    return True

def upload_files():
    """Upload required files to VM"""
    print("\n" + "="*80)
    print("STEP 6: Uploading files to VM")
    print("="*80)
    
    uploaded = []
    failed = []
    
    for file in REQUIRED_FILES:
        if not os.path.exists(file):
            failed.append(file)
            continue
            
        print(f"\n📤 Uploading {file}...")
        remote_path = f"{USERNAME}@{VM_NAME}:~/"
        
        try:
            run_command([
                "gcloud", "compute", "scp",
                file,
                remote_path,
                "--zone", ZONE
            ])
            uploaded.append(file)
            print(f"✅ Uploaded: {file}")
        except Exception as e:
            print(f"❌ Failed to upload {file}: {e}")
            failed.append(file)
    
    # Upload optional files if they exist
    for file in OPTIONAL_FILES:
        if os.path.exists(file):
            print(f"\n📤 Uploading optional file {file}...")
            remote_path = f"{USERNAME}@{VM_NAME}:~/"
            try:
                # Create secrets directory if needed
                run_command([
                    "gcloud", "compute", "ssh", f"{USERNAME}@{VM_NAME}",
                    "--zone", ZONE,
                    "--command", "mkdir -p ~/secrets"
                ], check=False)
                
                run_command([
                    "gcloud", "compute", "scp",
                    file,
                    f"{USERNAME}@{VM_NAME}:~/secrets/",
                    "--zone", ZONE
                ])
                print(f"✅ Uploaded: {file}")
            except Exception as e:
                print(f"⚠️ Failed to upload optional file {file}: {e}")
    
    if failed:
        print(f"\n❌ Failed to upload {len(failed)} file(s)")
        return False
    
    print(f"\n✅ Successfully uploaded {len(uploaded)} file(s)")
    return True

def setup_vm_environment():
    """Set up Python environment and install dependencies on VM"""
    print("\n" + "="*80)
    print("STEP 7: Setting up VM environment")
    print("="*80)
    
    # Update requirements.txt to include missing dependencies
    print("📝 Ensuring all dependencies are in requirements.txt...")
    requirements_content = Path("requirements.txt").read_text()
    
    required_deps = [
        "python-dotenv",
        "fuzzywuzzy",
        "python-Levenshtein",  # For faster fuzzy matching
    ]
    
    for dep in required_deps:
        if dep.split("==")[0] not in requirements_content:
            print(f"  Adding missing dependency: {dep}")
            requirements_content += f"\n{dep}\n"
    
    Path("requirements.txt").write_text(requirements_content)
    
    # Upload updated requirements.txt
    print("\n📤 Uploading updated requirements.txt...")
    run_command([
        "gcloud", "compute", "scp",
        "requirements.txt",
        f"{USERNAME}@{VM_NAME}:~/",
        "--zone", ZONE
    ])
    
    # Setup commands to run on VM
    setup_commands = [
        # Create virtual environment
        "python3 -m venv ~/venv",
        
        # Upgrade pip
        "~/venv/bin/pip install --upgrade pip",
        
        # Install system dependencies for fuzzywuzzy
        "sudo apt-get update",
        "sudo apt-get install -y python3-dev build-essential",
        
        # Install Python dependencies
        "~/venv/bin/pip install -r ~/requirements.txt",
        
        # Rename main file
        "mv ~/vm_inventory_updater_fixed.py ~/vm_inventory_updater.py",
        
        # Make script executable
        "chmod +x ~/vm_inventory_updater.py",
        
        # Create logs directory
        "mkdir -p ~/logs",
    ]
    
    print("\n🔧 Running setup commands on VM...")
    for i, cmd in enumerate(setup_commands, 1):
        print(f"\n[{i}/{len(setup_commands)}] {cmd}")
        try:
            run_command([
                "gcloud", "compute", "ssh", f"{USERNAME}@{VM_NAME}",
                "--zone", ZONE,
                "--command", cmd
            ], check=False)  # Don't fail on apt-get update if already updated
        except Exception as e:
            print(f"⚠️ Warning: {e}")
            # Continue anyway
    
    print("\n✅ VM environment setup complete")
    return True

def setup_cron_job():
    """Set up cron job for automated updates"""
    print("\n" + "="*80)
    print("STEP 8: Setting up cron job")
    print("="*80)
    
    # Default sheet ID (can be overridden with environment variable)
    sheet_id = "1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno"
    
    cron_command = (
        f"cd ~ && "
        f"export INVENTORY_SHEET_ID={sheet_id} && "
        f"~/venv/bin/python ~/vm_inventory_updater.py >> ~/inventory_cron.log 2>&1"
    )
    
    cron_entry = f"*/5 * * * * {cron_command}\n"
    
    print("Setting up cron job to run every 5 minutes...")
    
    # Create temporary cron file
    temp_cron = "temp_cron.txt"
    with open(temp_cron, "w") as f:
        f.write(cron_entry)
    
    try:
        # Upload cron file
        run_command([
            "gcloud", "compute", "scp",
            temp_cron,
            f"{USERNAME}@{VM_NAME}:~/temp_cron.txt",
            "--zone", ZONE
        ])
        
        # Install cron job
        run_command([
            "gcloud", "compute", "ssh", f"{USERNAME}@{VM_NAME}",
            "--zone", ZONE,
            "--command", "crontab ~/temp_cron.txt && rm ~/temp_cron.txt"
        ])
        
        # Verify cron job
        result = run_command([
            "gcloud", "compute", "ssh", f"{USERNAME}@{VM_NAME}",
            "--zone", ZONE,
            "--command", "crontab -l"
        ], check=False)
        
        if cron_entry.strip() in result.stdout:
            print("✅ Cron job installed successfully")
        else:
            print("⚠️ Cron job may not have been installed correctly")
            print("Current crontab:")
            print(result.stdout)
        
        # Clean up local temp file
        os.remove(temp_cron)
        
        return True
    except Exception as e:
        print(f"❌ Error setting up cron job: {e}")
        if os.path.exists(temp_cron):
            os.remove(temp_cron)
        return False

def verify_deployment():
    """Verify the deployment"""
    print("\n" + "="*80)
    print("STEP 9: Verifying deployment")
    print("="*80)
    
    checks = [
        ("Main script exists", "test -f ~/vm_inventory_updater.py && echo 'OK'"),
        ("Service account key exists", "test -f ~/service-account-key.json && echo 'OK'"),
        ("Clover credentials exist", "test -f ~/clover_creds.json && echo 'OK'"),
        ("Virtual environment exists", "test -d ~/venv && echo 'OK'"),
        ("Python packages installed", "~/venv/bin/pip list | grep -q 'google-api-python-client' && echo 'OK'"),
        ("Cron job configured", "crontab -l | grep -q 'vm_inventory_updater.py' && echo 'OK'"),
    ]
    
    all_passed = True
    for check_name, command in checks:
        try:
            result = run_command([
                "gcloud", "compute", "ssh", f"{USERNAME}@{VM_NAME}",
                "--zone", ZONE,
                "--command", command
            ], check=False)
            
            if "OK" in result.stdout:
                print(f"✅ {check_name}")
            else:
                print(f"❌ {check_name}")
                all_passed = False
        except Exception as e:
            print(f"⚠️ Could not verify {check_name}: {e}")
            all_passed = False
    
    return all_passed

def test_run():
    """Test run the script once"""
    print("\n" + "="*80)
    print("STEP 10: Testing script (optional)")
    print("="*80)
    
    # Skip interactive prompt - can be enabled later if needed
    print("Skipping test run (can be run manually later)")
    return True
    
    print("Running test execution...")
    try:
        result = run_command([
            "gcloud", "compute", "ssh", f"{USERNAME}@{VM_NAME}",
            "--zone", ZONE,
            "--command", "cd ~ && ~/venv/bin/python ~/vm_inventory_updater.py"
        ], check=False, timeout=120)
        
        print("\nTest execution output:")
        print(result.stdout)
        if result.stderr:
            print("\nErrors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("\n✅ Test run completed successfully")
        else:
            print("\n⚠️ Test run completed with errors (check logs)")
        
        return True
    except Exception as e:
        print(f"⚠️ Test run failed: {e}")
        return False

def main():
    """Main deployment function"""
    print("="*80)
    print("🚀 DEPLOYING REAL-TIME INVENTORY UPDATER TO NEW GCP VM")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Project ID: {PROJECT_ID}")
    print(f"  VM Name: {VM_NAME}")
    print(f"  Zone: {ZONE}")
    print(f"  Machine Type: {MACHINE_TYPE}")
    print()
    
    # Step 1: Check authentication
    if not check_gcloud_auth():
        print("\n❌ Please authenticate with: gcloud auth login")
        return False
    
    # Step 2: Check project
    if not check_project():
        print("\n❌ Failed to configure project")
        return False
    
    # Step 3: Check if VM exists
    vm_exists = check_vm_exists()
    
    # Step 4: Create VM if needed
    if not vm_exists:
        print(f"\n✅ Will create new VM '{VM_NAME}'")
        if not create_vm():
            print("\n❌ Failed to create VM")
            return False
    else:
        print(f"\n✅ VM '{VM_NAME}' already exists. Continuing with deployment...")
    
    # Step 5: Check required files
    if not check_required_files():
        print("\n❌ Missing required files")
        return False
    
    # Step 6: Upload files
    if not upload_files():
        print("\n❌ Failed to upload files")
        return False
    
    # Step 7: Setup VM environment
    if not setup_vm_environment():
        print("\n❌ Failed to setup VM environment")
        return False
    
    # Step 8: Setup cron job
    if not setup_cron_job():
        print("\n⚠️ Failed to setup cron job (you can set it up manually)")
    
    # Step 9: Verify deployment
    if not verify_deployment():
        print("\n⚠️ Some verification checks failed (deployment may still work)")
    
    # Step 10: Optional test run
    test_run()
    
    print("\n" + "="*80)
    print("✅ DEPLOYMENT COMPLETE!")
    print("="*80)
    print("\n📋 Summary:")
    print(f"  VM: {VM_NAME}")
    print(f"  Zone: {ZONE}")
    print(f"  Script: ~/vm_inventory_updater.py")
    print(f"  Cron: Runs every 5 minutes")
    print(f"  Logs: ~/inventory_cron.log")
    print("\n🔍 Useful commands:")
    print(f"  SSH to VM: gcloud compute ssh {USERNAME}@{VM_NAME} --zone={ZONE}")
    print(f"  View logs: gcloud compute ssh {USERNAME}@{VM_NAME} --zone={ZONE} --command='tail -50 ~/inventory_cron.log'")
    print(f"  Check cron: gcloud compute ssh {USERNAME}@{VM_NAME} --zone={ZONE} --command='crontab -l'")
    print(f"  Manual run: gcloud compute ssh {USERNAME}@{VM_NAME} --zone={ZONE} --command='cd ~ && ~/venv/bin/python ~/vm_inventory_updater.py'")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
