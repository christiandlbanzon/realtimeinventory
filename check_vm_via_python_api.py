#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check VM deployment using Google Cloud Python API
Uses service account credentials to access VM and check status
"""

import json
import os
import sys
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
import time

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")

# VM Configuration
VM_NAME = "inventory-updater-vm"
VM_ZONE = "us-central1-a"
VM_PROJECT = "boxwood-chassis-332307"
VM_USER = "banzo"
VM_HOME = f"/home/{VM_USER}"
LOG_FILE = f"{VM_HOME}/inventory_cron.log"
SCRIPT_FILE = f"{VM_HOME}/vm_inventory_updater.py"

def get_compute_service():
    """Get Compute Engine API service"""
    try:
        from google_auth_httplib2 import AuthorizedHttp
        import httplib2
        
        creds = service_account.Credentials.from_service_account_file(
            "service-account-key.json",
            scopes=['https://www.googleapis.com/auth/compute']
        )
        
        # Disable proxy for API calls
        http = httplib2.Http(proxy_info=None)
        authorized_http = AuthorizedHttp(creds, http=http)
        service = build('compute', 'v1', http=authorized_http)
        return service
    except Exception as e:
        print_error(f"Cannot create Compute service: {e}")
        return None

def check_vm_status(compute_service):
    """Check VM instance status"""
    print_header("1. CHECKING VM STATUS")
    
    try:
        instance = compute_service.instances().get(
            project=VM_PROJECT,
            zone=VM_ZONE,
            instance=VM_NAME
        ).execute()
        
        status = instance.get('status', 'UNKNOWN')
        
        if status == 'RUNNING':
            print_success(f"VM is running (status: {status})")
            
            # Get network info
            network_interfaces = instance.get('networkInterfaces', [])
            if network_interfaces:
                access_configs = network_interfaces[0].get('accessConfigs', [])
                if access_configs:
                    external_ip = access_configs[0].get('natIP', 'N/A')
                    print_info(f"  External IP: {external_ip}")
            
            # Get machine type
            machine_type = instance.get('machineType', '').split('/')[-1]
            print_info(f"  Machine Type: {machine_type}")
            
            return True
        else:
            print_error(f"VM is not running (status: {status})")
            return False
            
    except HttpError as e:
        print_error(f"Cannot access VM: {e}")
        return False
    except Exception as e:
        print_error(f"Error checking VM status: {e}")
        return False

def execute_vm_command(compute_service, command):
    """Execute a command on the VM using the Compute Engine API"""
    try:
        # Use the executeCommand API (available in newer versions)
        # If not available, we'll use a workaround
        
        # Try using the instances().executeCommand() method
        # Note: This requires OS Login or proper IAM permissions
        
        # Alternative: Use serial port output or metadata
        # For now, we'll try to use the executeCommand API
        
        request_body = {
            'command': command
        }
        
        try:
            response = compute_service.instances().executeCommand(
                project=VM_PROJECT,
                zone=VM_ZONE,
                instance=VM_NAME,
                body=request_body
            ).execute()
            
            return True, response.get('output', ''), ''
        except AttributeError:
            # executeCommand might not be available, use alternative method
            print_warning("executeCommand API not available, using alternative method...")
            return execute_vm_command_alternative(compute_service, command)
            
    except Exception as e:
        return False, '', str(e)

def execute_vm_command_via_gcloud(command):
    """Execute command on VM using gcloud CLI with service account"""
    import subprocess
    import tempfile
    import shutil
    
    try:
        # Find gcloud path
        gcloud_path = r"C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
        if not os.path.exists(gcloud_path):
            gcloud_path = 'gcloud'
        
        # Create temp config
        temp_config = tempfile.mkdtemp()
        env = os.environ.copy()
        env['CLOUDSDK_CONFIG'] = temp_config
        env['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath('service-account-key.json')
        
        # Remove proxy settings
        for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
            env.pop(proxy_var, None)
        
        # Authenticate gcloud with service account
        auth_result = subprocess.run(
            [gcloud_path, 'auth', 'activate-service-account',
             '--key-file', os.path.abspath('service-account-key.json'),
             '--quiet'],
            env=env,
            capture_output=True,
            timeout=30
        )
        
        # Execute command
        result = subprocess.run(
            [gcloud_path, 'compute', 'ssh', VM_NAME,
             '--zone', VM_ZONE,
             '--command', command],
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Clean up
        shutil.rmtree(temp_config, ignore_errors=True)
        
        return result.returncode == 0, result.stdout, result.stderr
        
    except Exception as e:
        return False, '', str(e)

def check_vm_files_via_api(compute_service):
    """Check if files exist on VM using gcloud SSH"""
    print_header("2. CHECKING FILES ON VM")
    
    files_to_check = [
        (SCRIPT_FILE, "Main inventory updater script"),
        (f"{VM_HOME}/clover_creds.json", "Clover credentials"),
        (f"{VM_HOME}/service-account-key.json", "Google service account"),
        (LOG_FILE, "Log file"),
    ]
    
    all_exist = True
    for file_path, description in files_to_check:
        success, output, error = execute_vm_command_via_gcloud(f"test -f {file_path} && echo 'EXISTS' || echo 'NOT_FOUND'")
        
        if success and 'EXISTS' in output:
            print_success(f"{description}: Found")
            
            # Get file size
            success_size, size_output, _ = execute_vm_command_via_gcloud(f"ls -lh {file_path} | awk '{{print $5}}'")
            if success_size:
                print_info(f"  Size: {size_output.strip()}")
        else:
            print_error(f"{description}: NOT FOUND ({file_path})")
            all_exist = False
    
    return all_exist

def check_vm_logs_via_api(compute_service):
    """Check VM logs via gcloud SSH"""
    print_header("3. CHECKING VM LOGS")
    
    # Check if log file exists
    success, output, error = execute_vm_command_via_gcloud(f"test -f {LOG_FILE} && echo 'EXISTS' || echo 'NOT_FOUND'")
    
    if not success or 'NOT_FOUND' in output:
        print_error(f"Log file not found: {error}")
        return False
    
    print_success("Log file exists")
    
    # Get recent log entries
    success, output, error = execute_vm_command_via_gcloud(f"tail -100 {LOG_FILE}")
    
    if not success:
        print_error(f"Cannot read log file: {error}")
        return False
    
    log_lines = output.strip().split('\n')
    
    if not log_lines or len(log_lines) < 5:
        print_warning("Log file exists but has very few entries")
        return False
    
    print_success(f"Found {len(log_lines)} recent log entries")
    
    # Look for recent successful completions
    success_lines = [line for line in log_lines if 'completed successfully' in line.lower() or 'Script completed' in line]
    
    if success_lines:
        print_success(f"Found {len(success_lines)} successful completion(s)")
        print_info("  Most recent:")
        for line in success_lines[-3:]:
            print(f"    {line[:150]}...")
    else:
        print_warning("No successful completions found in recent logs")
    
    # Check for errors
    error_lines = [line for line in log_lines if 'ERROR' in line or 'error' in line.lower() or 'Exception' in line]
    
    if error_lines:
        print_warning(f"Found {len(error_lines)} error(s) in recent logs")
        print_info("  Recent errors:")
        for line in error_lines[-5:]:
            print(f"    {line[:150]}...")
    else:
        print_success("No errors found in recent logs")
    
    # Check last run timestamp
    last_run_lines = [line for line in log_lines if 'Script completed' in line or 'Update completed' in line]
    if last_run_lines:
        last_line = last_run_lines[-1]
        print_info(f"  Last run: {last_line[:200]}")
    
    return True

def check_cron_configuration():
    """Check cron job configuration"""
    print_header("4. CHECKING CRON CONFIGURATION")
    
    success, output, error = execute_vm_command_via_gcloud("crontab -l")
    
    if not success:
        print_error("Cannot read crontab")
        return False
    
    cron_lines = output.strip().split('\n')
    
    # Look for inventory updater cron job
    inventory_cron = None
    for line in cron_lines:
        if 'vm_inventory_updater' in line or 'inventory' in line.lower():
            inventory_cron = line
            break
    
    if inventory_cron:
        print_success("Cron job found")
        print_info(f"  {inventory_cron}")
        
        # Check schedule
        if '*/5' in inventory_cron:
            print_success("  Schedule: Every 5 minutes ✓")
        else:
            print_warning("  Schedule: Not every 5 minutes")
        
        # Check sheet ID
        if 'INVENTORY_SHEET_ID' in inventory_cron:
            print_success("  Sheet ID environment variable set ✓")
        else:
            print_warning("  Sheet ID environment variable not found")
        
        return True
    else:
        print_error("Inventory updater cron job NOT FOUND")
        print_info("Current crontab:")
        for line in cron_lines:
            print(f"  {line}")
        return False

def check_vm_disk(compute_service):
    """Check VM disk status"""
    print_header("5. CHECKING VM DISK STATUS")
    
    try:
        instance = compute_service.instances().get(
            project=VM_PROJECT,
            zone=VM_ZONE,
            instance=VM_NAME
        ).execute()
        
        disks = instance.get('disks', [])
        
        if disks:
            print_success(f"Found {len(disks)} disk(s)")
            for disk in disks:
                disk_name = disk.get('deviceName', 'Unknown')
                disk_type = disk.get('type', '').split('/')[-1]
                boot = disk.get('boot', False)
                boot_status = " (Boot)" if boot else ""
                print_info(f"  {disk_name}: {disk_type}{boot_status}")
        
        return True
        
    except Exception as e:
        print_error(f"Cannot check disk status: {e}")
        return False

def get_vm_recommendations():
    """Provide recommendations for better VM access"""
    print_header("RECOMMENDATIONS")
    
    print_info("For full VM verification, consider:")
    print("  1. Enable OS Login for easier SSH access")
    print("  2. Use Cloud Logging API for better log access")
    print("  3. Set up Cloud Monitoring for automated health checks")
    print("  4. Use gcloud CLI for direct SSH command execution")
    
    print_info("\nTo check logs via SSH (if OS Login is enabled):")
    print(f"  gcloud compute ssh {VM_NAME} --zone={VM_ZONE} --command='tail -50 {LOG_FILE}'")
    
    print_info("\nTo check cron configuration:")
    print(f"  gcloud compute ssh {VM_NAME} --zone={VM_ZONE} --command='crontab -l'")

def main():
    print_header("VM DEPLOYMENT CHECK VIA PYTHON API")
    print_info(f"VM: {VM_NAME} (zone: {VM_ZONE}, project: {VM_PROJECT})")
    print_info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get Compute service
    compute_service = get_compute_service()
    if not compute_service:
        print_error("Cannot initialize Compute Engine API service")
        print_info("Make sure service-account-key.json exists and has proper permissions")
        return False
    
    results = {}
    
    # Run checks
    results['vm_status'] = check_vm_status(compute_service)
    results['vm_files'] = check_vm_files_via_api(compute_service)
    results['vm_logs'] = check_vm_logs_via_api(compute_service)
    results['cron_config'] = check_cron_configuration()
    results['vm_disk'] = check_vm_disk(compute_service)
    
    # Summary
    print_header("CHECK SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} checks passed{Colors.END}\n")
    
    for check_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {check_name.replace('_', ' ').title()}: {status}")
    
    # Critical check
    if results.get('vm_status'):
        print_success("\nVM is running and accessible via API")
    else:
        print_error("\nVM is not accessible - check VM status and permissions")
    
    # Recommendations
    get_vm_recommendations()
    
    print_info(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return all(results.values())

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nCheck interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
