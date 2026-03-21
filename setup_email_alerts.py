"""Setup script for error alert system"""
import os
import sys

def setup_alert_system():
    """Setup email alert system"""
    print("="*80)
    print("EMAIL ALERT SYSTEM SETUP")
    print("="*80)
    
    print("\nThis will set up automated email alerts for inventory updater errors.")
    print("\nYou'll need:")
    print("1. Gmail account")
    print("2. Gmail App Password (generate at: https://myaccount.google.com/apppasswords)")
    
    print("\n" + "-"*80)
    print("STEP 1: Configure Email Settings")
    print("-"*80)
    
    email_from = input("\nEnter your Gmail address (e.g., yourname@gmail.com): ").strip()
    email_to = input("Enter recipient email (can be same): ").strip() or email_from
    
    print("\n" + "-"*80)
    print("STEP 2: Generate Gmail App Password")
    print("-"*80)
    print("\n1. Go to: https://myaccount.google.com/security")
    print("2. Sign in with your Google account")
    print("3. Scroll down to '2-Step Verification' section")
    print("4. Click on '2-Step Verification' (must be enabled first)")
    print("5. Scroll down and click 'App passwords'")
    print("6. Select 'Mail' and 'Other (Custom name)'")
    print("7. Enter 'Inventory Alerts' as the name")
    print("8. Click 'Generate'")
    print("9. Copy the 16-character password (no spaces)")
    
    app_password = input("\nPaste your Gmail App Password here: ").strip().replace(" ", "")
    
    if not app_password or len(app_password) != 16:
        print("\n⚠️  Warning: App password should be 16 characters. Continuing anyway...")
    
    print("\n" + "-"*80)
    print("STEP 3: Update Configuration")
    print("-"*80)
    
    # Read the script
    script_path = "error_alert_system.py"
    with open(script_path, 'r') as f:
        content = f.read()
    
    # Update email settings
    content = content.replace('EMAIL_FROM = "your-email@gmail.com"', f'EMAIL_FROM = "{email_from}"')
    content = content.replace('EMAIL_TO = "your-email@gmail.com"', f'EMAIL_TO = "{email_to}"')
    
    # Write back
    with open(script_path, 'w') as f:
        f.write(content)
    
    print(f"\n✅ Updated {script_path} with your email settings")
    
    print("\n" + "-"*80)
    print("STEP 4: Set Environment Variable")
    print("-"*80)
    print("\nSet the email password as an environment variable:")
    print(f"\nWindows PowerShell:")
    print(f'  $env:EMAIL_PASSWORD="{app_password}"')
    print(f"\nWindows CMD:")
    print(f'  set EMAIL_PASSWORD={app_password}')
    print(f"\nLinux/Mac:")
    print(f'  export EMAIL_PASSWORD="{app_password}"')
    
    print("\n" + "-"*80)
    print("STEP 5: Test Email")
    print("-"*80)
    
    test = input("\nTest email now? (y/n): ").strip().lower()
    if test == 'y':
        os.environ['EMAIL_PASSWORD'] = app_password
        from error_alert_system import send_email
        
        print("\nSending test email...")
        if send_email(
            "Test: Inventory Updater Alert System",
            "This is a test email from the Inventory Updater Alert System.\n\nIf you received this, the system is configured correctly!",
            "<html><body><h2>Test Email</h2><p>This is a test email from the Inventory Updater Alert System.</p><p>If you received this, the system is configured correctly!</p></body></html>"
        ):
            print("\n✅ Test email sent successfully!")
        else:
            print("\n❌ Failed to send test email. Check your settings.")
    
    print("\n" + "-"*80)
    print("STEP 6: Schedule Monitoring")
    print("-"*80)
    print("\nTo run monitoring every 15 minutes, add to cron:")
    print("\nOption 1: Run locally (on your machine):")
    print("  Add to Windows Task Scheduler or cron:")
    print(f'  python "{os.path.abspath("error_alert_system.py")}"')
    
    print("\nOption 2: Run on VM (recommended):")
    print("  Upload script to VM and add to VM cron:")
    print("  gcloud compute scp error_alert_system.py inventory-updater-vm:/home/banzo/ --zone=us-central1-a")
    print("  gcloud compute ssh inventory-updater-vm --zone=us-central1-a")
    print("  crontab -e")
    print("  Add: */15 * * * * cd /home/banzo && export EMAIL_PASSWORD='your-password' && python3 error_alert_system.py >> error_alerts.log 2>&1")
    
    print("\n" + "="*80)
    print("SETUP COMPLETE!")
    print("="*80)
    print("\nThe alert system will:")
    print("  ✅ Check for errors every 15 minutes")
    print("  ✅ Send email alerts when issues are detected")
    print("  ✅ Include status summary and error details")
    print("\nRemember to set EMAIL_PASSWORD environment variable!")

if __name__ == "__main__":
    setup_alert_system()

