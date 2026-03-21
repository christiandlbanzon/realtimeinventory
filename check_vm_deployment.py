#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive VM deployment check for real-time inventory updater
Checks:
1. VM status and accessibility
2. Cron job configuration
3. Recent log entries and errors
4. Script files on VM
5. Credentials on VM
6. Recent execution status
"""

import subprocess
import sys
import json
from datetime import datetime

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
VM_USER = "banzo"
VM_HOME = f"/home/{VM_USER}"
LOG_FILE = f"{VM_HOME}/inventory_cron.log"
SCRIPT_FILE = f"{VM_HOME}/vm_inventory_updater.py"

def run_vm_command(command, timeout=30):
    """Run a command on the VM via gcloud ssh"""
    try:
        full_command = [
            'gcloud', 'compute', 'ssh', VM_NAME,
            '--zone', VM_ZONE,
            '--command', command
        ]
        
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

# ============================================================================
# 1. CHECK VM STATUS
# ============================================================================

def check_vm_status():
    """Check if VM is running and accessible"""
    print_header("1. CHECKING VM STATUS")
    
    try:
        # Check VM instance status
        result = subprocess.run(
            ['gcloud', 'compute', 'instances', 'describe', VM_NAME,
             '--zone', VM_ZONE, '--format', 'json'],
            capture_output=True,
            text=True,
            timeout=20
        )
        
        if result.returncode != 0:
            print_error(f"Cannot access VM: {result.stderr}")
            return False
        
        vm_info = json.loads(result.stdout)
        status = vm_info.get('status', 'UNKNOWN')
        
        if status == 'RUNNING':
            print_success(f"VM is running (status: {status})")
            
            # Get IP address
            network_interfaces = vm_info.get('networkInterfaces', [])
            if network_interfaces:
                access_configs = network_interfaces[0].get('accessConfigs', [])
                if access_configs:
                    external_ip = access_configs[0].get('natIP', 'N/A')
                    print_info(f"  External IP: {external_ip}")
            
            return True
        else:
            print_error(f"VM is not running (status: {status})")
            return False
            
    except json.JSONDecodeError:
        print_error("Invalid JSON response from gcloud")
        return False
    except Exception as e:
        print_error(f"Error checking VM status: {e}")
        return False

# ============================================================================
# 2. CHECK SSH ACCESS
# ============================================================================

def check_ssh_access():
    """Check if we can SSH into the VM"""
    print_header("2. CHECKING SSH ACCESS")
    
    success, output, error = run_vm_command("echo 'SSH connection test'")
    
    if success:
        print_success("SSH access successful")
        return True
    else:
        print_error(f"SSH access failed: {error}")
        return False

# ============================================================================
# 3. CHECK FILES ON VM
# ============================================================================

def check_vm_files():
    """Check if required files exist on VM"""
    print_header("3. CHECKING FILES ON VM")
    
    files_to_check = [
        (SCRIPT_FILE, "Main inventory updater script"),
        (f"{VM_HOME}/clover_creds.json", "Clover credentials"),
        (f"{VM_HOME}/service-account-key.json", "Google service account"),
        (LOG_FILE, "Log file"),
    ]
    
    all_exist = True
    for file_path, description in files_to_check:
        success, output, error = run_vm_command(f"test -f {file_path} && echo 'EXISTS' || echo 'NOT_FOUND'")
        
        if success and 'EXISTS' in output:
            print_success(f"{description}: Found")
            
            # Get file size
            success_size, size_output, _ = run_vm_command(f"ls -lh {file_path} | awk '{{print $5}}'")
            if success_size:
                print_info(f"  Size: {size_output.strip()}")
        else:
            print_error(f"{description}: NOT FOUND ({file_path})")
            all_exist = False
    
    return all_exist

# ============================================================================
# 4. CHECK CRON CONFIGURATION
# ============================================================================

def check_cron_config():
    """Check cron job configuration"""
    print_header("4. CHECKING CRON CONFIGURATION")
    
    success, output, error = run_vm_command("crontab -l")
    
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

# ============================================================================
# 5. CHECK RECENT LOGS
# ============================================================================

def check_recent_logs():
    """Check recent log entries"""
    print_header("5. CHECKING RECENT LOGS")
    
    # Check if log file exists and get recent entries
    success, output, error = run_vm_command(f"tail -100 {LOG_FILE} 2>&1")
    
    if not success or 'No such file' in output:
        print_error(f"Log file not found or cannot be read: {error}")
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
            # Extract timestamp if available
            print(f"    {line[:100]}...")
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

# ============================================================================
# 6. CHECK SCRIPT EXECUTION STATUS
# ============================================================================

def check_script_execution():
    """Check if script is currently running or recently ran"""
    print_header("6. CHECKING SCRIPT EXECUTION STATUS")
    
    # Check if process is running
    success, output, error = run_vm_command("ps aux | grep vm_inventory_updater | grep -v grep")
    
    if success and output.strip():
        print_warning("Script appears to be currently running")
        print_info("  Running processes:")
        for line in output.strip().split('\n'):
            print(f"    {line[:100]}")
    else:
        print_info("Script is not currently running (expected if running via cron)")
    
    # Check last modification time of log file
    success, output, error = run_vm_command(f"stat -c '%y' {LOG_FILE} 2>&1 || stat -f '%Sm' {LOG_FILE} 2>&1")
    
    if success:
        print_info(f"Log file last modified: {output.strip()}")
    
    # Check for very recent log entries (last 10 minutes)
    success, output, error = run_vm_command(
        f"find {LOG_FILE} -mmin -10 -type f 2>&1 && echo 'RECENT' || echo 'NOT_RECENT'"
    )
    
    if success and 'RECENT' in output:
        print_success("Log file was modified in last 10 minutes (script is active)")
    else:
        print_warning("Log file was NOT modified in last 10 minutes")
        print_info("  This might indicate the script is not running")
    
    return True

# ============================================================================
# 7. CHECK CREDENTIALS ON VM
# ============================================================================

def check_vm_credentials():
    """Check if credentials files exist and are valid on VM"""
    print_header("7. CHECKING CREDENTIALS ON VM")
    
    # Check Clover credentials
    success, output, error = run_vm_command(
        f"python3 -c \"import json; f=open('{VM_HOME}/clover_creds.json'); d=json.load(f); print(f'VALID: {{len(d)}} locations')\" 2>&1"
    )
    
    if success and 'VALID' in output:
        print_success("Clover credentials file is valid JSON")
        print_info(f"  {output.strip()}")
    else:
        print_error(f"Clover credentials file is invalid or missing: {error}")
    
    # Check Google service account
    success, output, error = run_vm_command(
        f"python3 -c \"import json; f=open('{VM_HOME}/service-account-key.json'); d=json.load(f); print('VALID' if d.get('type')=='service_account' else 'INVALID')\" 2>&1"
    )
    
    if success and 'VALID' in output:
        print_success("Google service account file is valid")
    else:
        print_error(f"Google service account file is invalid or missing: {error}")
    
    return True

# ============================================================================
# 8. CHECK PYTHON ENVIRONMENT
# ============================================================================

def check_python_environment():
    """Check Python environment on VM"""
    print_header("8. CHECKING PYTHON ENVIRONMENT")
    
    # Check Python version
    success, output, error = run_vm_command(f"{VM_HOME}/venv/bin/python --version 2>&1")
    
    if success:
        print_success(f"Python version: {output.strip()}")
    else:
        print_warning(f"Virtual environment Python not found: {error}")
        
        # Try system Python
        success, output, error = run_vm_command("python3 --version 2>&1")
        if success:
            print_info(f"System Python: {output.strip()}")
    
    # Check if required packages are installed
    required_packages = ['google-api-python-client', 'requests']
    
    for package in required_packages:
        success, output, error = run_vm_command(
            f"{VM_HOME}/venv/bin/python -c \"import {package.replace('-', '_')}; print('INSTALLED')\" 2>&1 || echo 'NOT_INSTALLED'"
        )
        
        if success and 'INSTALLED' in output:
            print_success(f"  {package}: Installed")
        else:
            print_error(f"  {package}: NOT installed")
    
    return True

# ============================================================================
# 9. TEST MANUAL EXECUTION
# ============================================================================

def test_manual_execution():
    """Test if script can be executed manually"""
    print_header("9. TESTING MANUAL EXECUTION (Dry Run)")
    
    print_info("Attempting to run script with --help or similar to verify it's executable...")
    
    # Try to check if script exists and is executable
    success, output, error = run_vm_command(
        f"cd {VM_HOME} && {VM_HOME}/venv/bin/python {SCRIPT_FILE} --help 2>&1 | head -20 || echo 'SCRIPT_RUN_TEST'"
    )
    
    if success:
        if 'SCRIPT_RUN_TEST' in output:
            print_info("Script file exists and Python can access it")
        else:
            print_info("Script help output:")
            print(f"  {output[:500]}")
    
    return True

# ============================================================================
# MAIN
# ============================================================================

def main():
    print_header("COMPREHENSIVE VM DEPLOYMENT CHECK")
    print_info(f"VM: {VM_NAME} (zone: {VM_ZONE})")
    print_info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Run all checks
    results['vm_status'] = check_vm_status()
    results['ssh_access'] = check_ssh_access()
    results['vm_files'] = check_vm_files()
    results['cron_config'] = check_cron_config()
    results['recent_logs'] = check_recent_logs()
    results['script_execution'] = check_script_execution()
    results['vm_credentials'] = check_vm_credentials()
    results['python_env'] = check_python_environment()
    results['manual_test'] = test_manual_execution()
    
    # Summary
    print_header("CHECK SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} checks passed{Colors.END}\n")
    
    for check_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {check_name.replace('_', ' ').title()}: {status}")
    
    # Critical issues
    critical_issues = []
    if not results.get('vm_status'):
        critical_issues.append("VM is not running")
    if not results.get('ssh_access'):
        critical_issues.append("Cannot SSH into VM")
    if not results.get('cron_config'):
        critical_issues.append("Cron job not configured")
    if not results.get('recent_logs'):
        critical_issues.append("No recent log activity")
    
    if critical_issues:
        print(f"\n{Colors.RED}{Colors.BOLD}CRITICAL ISSUES:{Colors.END}")
        for issue in critical_issues:
            print(f"  ❌ {issue}")
    else:
        print(f"\n{Colors.GREEN}{Colors.BOLD}All critical checks passed!{Colors.END}")
    
    print_info(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return passed == total

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
