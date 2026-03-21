"""Email error alert system for VM inventory updater"""
import smtplib
import subprocess
import sys
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# Configuration - Update these with your email details
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_FROM = "your-email@gmail.com"  # Your Gmail address
EMAIL_TO = "your-email@gmail.com"  # Where to send alerts
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # Use app password for Gmail

# Optional: App password if using Gmail
# Generate at: https://myaccount.google.com/security
# Then go to: 2-Step Verification > App passwords

VM_NAME = "inventory-updater-vm"
VM_ZONE = "us-central1-a"
LOG_FILE = "/home/banzo/inventory_cron.log"
STATE_FILE = "/tmp/error_alert_last_check.txt"  # On VM

def send_email(subject, body, html_body=None):
    """Send email alert"""
    if not EMAIL_PASSWORD:
        print("WARNING: EMAIL_PASSWORD not set. Cannot send email.")
        print("Set it with: export EMAIL_PASSWORD='your-app-password'")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        msg['Subject'] = subject
        
        # Add plain text version
        text_part = MIMEText(body, 'plain')
        msg.attach(text_part)
        
        # Add HTML version if provided
        if html_body:
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
        
        # Send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"Email sent successfully to {EMAIL_TO}")
        return True
        
    except Exception as e:
        print(f"ERROR sending email: {e}")
        return False

def check_vm_logs():
    """Check VM logs for errors"""
    try:
        # Get recent errors from last hour
        cmd = f"tail -1000 {LOG_FILE} | grep -i 'ERROR' | tail -20"
        result = subprocess.run(
            ['gcloud', 'compute', 'ssh', VM_NAME,
             '--zone', VM_ZONE,
             '--command', cmd],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            errors = result.stdout.strip()
            return errors.split('\n') if errors else []
        else:
            print(f"Error checking logs: {result.stderr}")
            return []
            
    except Exception as e:
        print(f"Exception checking logs: {e}")
        return []

def check_last_run():
    """Check when script last ran successfully"""
    try:
        cmd = f"tail -100 {LOG_FILE} | grep 'Script completed successfully' | tail -1"
        result = subprocess.run(
            ['gcloud', 'compute', 'ssh', VM_NAME,
             '--zone', VM_ZONE,
             '--command', cmd],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
        
    except Exception as e:
        print(f"Error checking last run: {e}")
        return None

def check_cron_status():
    """Check if cron job is configured"""
    try:
        cmd = "crontab -l | grep vm_inventory"
        result = subprocess.run(
            ['gcloud', 'compute', 'ssh', VM_NAME,
             '--zone', VM_ZONE,
             '--command', cmd],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return True, result.stdout.strip()
        return False, None
        
    except Exception as e:
        print(f"Error checking cron: {e}")
        return False, None

def check_column_detection():
    """Check if column detection is working"""
    try:
        cmd = f"tail -200 {LOG_FILE} | grep 'Location columns found' | tail -1"
        result = subprocess.run(
            ['gcloud', 'compute', 'ssh', VM_NAME,
             '--zone', VM_ZONE,
             '--command', cmd],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
        
    except Exception as e:
        print(f"Error checking columns: {e}")
        return None

def format_email_body(errors, last_run, cron_status, column_status):
    """Format email body"""
    body = f"""
INVENTORY UPDATER ERROR ALERT
============================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

STATUS SUMMARY:
--------------
"""
    
    # Cron status
    cron_ok, cron_line = cron_status
    if cron_ok:
        body += f"✅ Cron Job: Configured\n   {cron_line}\n\n"
    else:
        body += f"❌ Cron Job: NOT CONFIGURED!\n\n"
    
    # Last run
    if last_run:
        body += f"✅ Last Run: {last_run}\n\n"
    else:
        body += f"⚠️  Last Run: NOT FOUND (script may not be running)\n\n"
    
    # Column detection
    if column_status:
        if "Old San Juan" in column_status and "San Patricio" in column_status:
            body += f"✅ Column Detection: Working\n   {column_status}\n\n"
        else:
            body += f"⚠️  Column Detection: Partial\n   {column_status}\n\n"
    else:
        body += f"❌ Column Detection: NOT FOUND\n\n"
    
    # Errors
    if errors:
        body += f"🚨 ERRORS FOUND ({len(errors)}):\n"
        body += "-" * 50 + "\n"
        for i, error in enumerate(errors[-10:], 1):  # Last 10 errors
            body += f"{i}. {error}\n"
        body += "\n"
    else:
        body += "✅ No errors found in recent logs\n\n"
    
    body += """
NEXT STEPS:
----------
1. Check logs: gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -100 /home/banzo/inventory_cron.log"

2. Manual test: gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && export INVENTORY_SHEET_ID=1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno && /home/banzo/venv/bin/python vm_inventory_updater.py"

3. Check cron: gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="crontab -l"

For more details, see ERROR_HANDLING_GUIDE.md
"""
    
    return body

def format_html_email(errors, last_run, cron_status, column_status):
    """Format HTML email"""
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .header {{ background-color: #f44336; color: white; padding: 20px; }}
            .content {{ padding: 20px; }}
            .error {{ color: #d32f2f; font-weight: bold; }}
            .warning {{ color: #f57c00; }}
            .success {{ color: #388e3c; }}
            .section {{ margin: 20px 0; padding: 15px; background-color: #f5f5f5; }}
            pre {{ background-color: #263238; color: #aed581; padding: 10px; overflow-x: auto; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>🚨 Inventory Updater Error Alert</h2>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="content">
            <div class="section">
                <h3>Status Summary</h3>
"""
    
    # Cron status
    cron_ok, cron_line = cron_status
    if cron_ok:
        html += f"<p class='success'>✅ Cron Job: Configured</p><pre>{cron_line}</pre>"
    else:
        html += f"<p class='error'>❌ Cron Job: NOT CONFIGURED!</p>"
    
    # Last run
    if last_run:
        html += f"<p class='success'>✅ Last Run: {last_run}</p>"
    else:
        html += f"<p class='warning'>⚠️ Last Run: NOT FOUND</p>"
    
    # Column detection
    if column_status:
        html += f"<p class='success'>✅ Column Detection: Working</p><pre>{column_status}</pre>"
    else:
        html += f"<p class='error'>❌ Column Detection: NOT FOUND</p>"
    
    html += """
            </div>
            
            <div class="section">
                <h3>Recent Errors</h3>
"""
    
    if errors:
        html += f"<p class='error'>🚨 Found {len(errors)} errors:</p><ul>"
        for error in errors[-10:]:
            html += f"<li>{error}</li>"
        html += "</ul>"
    else:
        html += "<p class='success'>✅ No errors found</p>"
    
    html += """
            </div>
            
            <div class="section">
                <h3>Quick Actions</h3>
                <pre>
# Check logs
gcloud compute ssh inventory-updater-vm --zone=us-central1-a \\
  --command="tail -100 /home/banzo/inventory_cron.log"

# Manual test
gcloud compute ssh inventory-updater-vm --zone=us-central1-a \\
  --command="cd /home/banzo && export INVENTORY_SHEET_ID=1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno && /home/banzo/venv/bin/python vm_inventory_updater.py"
                </pre>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def should_send_alert(errors, last_run, cron_status):
    """Determine if alert should be sent"""
    cron_ok, _ = cron_status
    
    # Alert if:
    # 1. Cron not configured
    if not cron_ok:
        return True, "CRITICAL: Cron job not configured"
    
    # 2. Script hasn't run in last 15 minutes
    if not last_run:
        return True, "WARNING: Script not running"
    
    # 3. Recent errors found
    if errors:
        # Check if errors are recent (within last hour)
        recent_errors = [e for e in errors if any(x in e for x in [
            datetime.now().strftime('%Y-%m-%d'),
            (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d')
        ])]
        if recent_errors:
            return True, f"ERROR: Found {len(recent_errors)} recent errors"
    
    return False, None

def main():
    """Main monitoring function"""
    print(f"Checking VM status at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    
    # Check all statuses
    errors = check_vm_logs()
    last_run = check_last_run()
    cron_status = check_cron_status()
    column_status = check_column_detection()
    
    # Determine if alert needed
    should_alert, alert_reason = should_send_alert(errors, last_run, cron_status)
    
    if should_alert:
        print(f"\n⚠️  Alert triggered: {alert_reason}")
        
        # Format email
        subject = f"🚨 Inventory Updater Alert: {alert_reason}"
        body = format_email_body(errors, last_run, cron_status, column_status)
        html_body = format_html_email(errors, last_run, cron_status, column_status)
        
        # Send email
        if send_email(subject, body, html_body):
            print("✅ Alert email sent successfully")
        else:
            print("❌ Failed to send alert email")
            return False
    else:
        print("\n✅ No alerts needed - system running normally")
        return True
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

