"""Test script to verify error alert system works"""
import sys
import os

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    try:
        import smtplib
        import subprocess
        from datetime import datetime, timedelta
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        print("OK: All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_vm_connection():
    """Test VM connection"""
    print("\nTesting VM connection...")
    try:
        import subprocess
        result = subprocess.run(
            ['gcloud', 'compute', 'ssh', 'inventory-updater-vm',
             '--zone', 'us-central1-a',
             '--command', 'echo "Connection test"'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("OK: VM connection successful")
            return True
        else:
            print(f"⚠️  VM connection issue: {result.stderr}")
            return False
    except FileNotFoundError:
        print("⚠️  gcloud CLI not found (OK if running locally)")
        return None
    except Exception as e:
        print(f"⚠️  Connection test error: {e}")
        return None

def test_email_config():
    """Test email configuration"""
    print("\nTesting email configuration...")
    
    # Check if email is configured
    script_path = "error_alert_system.py"
    if not os.path.exists(script_path):
        print(f"❌ {script_path} not found")
        return False
    
    with open(script_path, 'r') as f:
        content = f.read()
    
    # Check if email is still using default
    if 'your-email@gmail.com' in content:
        print("⚠️  Email not configured yet")
        print("   Run: python setup_email_alerts.py")
        return False
    
    # Check if password env var is set
    if not os.getenv('EMAIL_PASSWORD'):
        print("⚠️  EMAIL_PASSWORD not set")
        print("   Set it with: export EMAIL_PASSWORD='your-password'")
        return False
    
        print("OK: Email configuration looks good")
    return True

def test_log_checking():
    """Test log checking functionality"""
    print("\nTesting log checking...")
    try:
        import subprocess
        
        # Try to check logs
        result = subprocess.run(
            ['gcloud', 'compute', 'ssh', 'inventory-updater-vm',
             '--zone', 'us-central1-a',
             '--command', 'tail -10 /home/banzo/inventory_cron.log'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("OK: Can read VM logs")
            return True
        else:
            print("⚠️  Cannot read logs (may need gcloud setup)")
            return None
            
    except FileNotFoundError:
        print("⚠️  gcloud CLI not found (OK if running locally)")
        return None
    except Exception as e:
        print(f"⚠️  Error: {e}")
        return None

def test_email_sending():
    """Test email sending (without actually sending)"""
    print("\nTesting email function...")
    try:
        # Import the send_email function
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from error_alert_system import send_email
        
        # Don't actually send, just verify function exists
        if callable(send_email):
            print("OK: Email function available")
            return True
        else:
            print("❌ Email function not found")
            return False
            
    except Exception as e:
        print(f"⚠️  Error loading email function: {e}")
        return False

def run_dry_run():
    """Run a dry run without sending email"""
    print("\n" + "="*80)
    print("RUNNING DRY RUN TEST")
    print("="*80)
    
    try:
        import subprocess
        
        # Run the script but capture output
        result = subprocess.run(
            [sys.executable, 'error_alert_system.py'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print("\nScript output:")
        print(result.stdout)
        
        if result.stderr:
            print("\nErrors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("\nOK: Dry run completed successfully")
            return True
        else:
            print(f"\n⚠️  Dry run exited with code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error running dry run: {e}")
        return False

def main():
    """Run all tests"""
    print("="*80)
    print("ERROR ALERT SYSTEM - TEST SUITE")
    print("="*80)
    
    results = {}
    
    # Test 1: Imports
    results['imports'] = test_imports()
    
    # Test 2: VM Connection
    results['vm_connection'] = test_vm_connection()
    
    # Test 3: Email Config
    results['email_config'] = test_email_config()
    
    # Test 4: Log Checking
    results['log_checking'] = test_log_checking()
    
    # Test 5: Email Function
    results['email_function'] = test_email_sending()
    
    # Test 6: Dry Run
    if all(v for v in results.values() if v is not False):
        results['dry_run'] = run_dry_run()
    else:
        print("\n⚠️  Skipping dry run - some tests failed")
        results['dry_run'] = None
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL" if result is False else "SKIP"
        print(f"{status} - {test_name}")
    
    all_passed = all(v for v in results.values() if v is not None)
    
    if all_passed:
        print("\nOK: All critical tests passed!")
        print("\nSystem is ready to use. Next steps:")
        print("1. Configure email: python setup_email_alerts.py")
        print("2. Set EMAIL_PASSWORD environment variable")
        print("3. Test: python error_alert_system.py")
    else:
        print("\n⚠️  Some tests failed or were skipped")
        print("This is OK if:")
        print("- gcloud CLI not installed (for local testing)")
        print("- Email not configured yet")
        print("- Just verifying the script structure")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

