# EMAIL ALERT SYSTEM - Quick Setup Guide

## 🚀 Quick Setup

### Step 1: Run Setup Script
```bash
python setup_email_alerts.py
```

This will:
- Ask for your email address
- Guide you through Gmail App Password setup
- Configure the alert system
- Test email sending

### Step 2: Generate Gmail App Password

**Important:** You must have 2-Step Verification enabled first!

1. Go to: https://myaccount.google.com/security
2. Sign in with your Google account
3. Scroll down to **"2-Step Verification"** section
4. Click on **"2-Step Verification"** (enable it if not already enabled)
5. Scroll down on the 2-Step Verification page
6. Click **"App passwords"** (at the bottom)
7. Select:
   - App: **Mail**
   - Device: **Other (Custom name)**
   - Name: **Inventory Alerts**
8. Click **Generate**
9. Copy the 16-character password (no spaces)

**Note:** If you don't see "App passwords", make sure 2-Step Verification is enabled first.

### Step 3: Set Environment Variable

**Windows PowerShell:**
```powershell
$env:EMAIL_PASSWORD="your-16-char-password"
```

**Windows CMD:**
```cmd
set EMAIL_PASSWORD=your-16-char-password
```

**Linux/Mac:**
```bash
export EMAIL_PASSWORD="your-16-char-password"
```

### Step 4: Test the System

```bash
python error_alert_system.py
```

This will check for errors and send an email if any are found.

---

## 📅 Scheduling Alerts

### Option 1: Run Locally (Your Computer)

**Windows Task Scheduler:**
1. Open Task Scheduler
2. Create Basic Task
3. Name: "Inventory Error Alerts"
4. Trigger: Every 15 minutes
5. Action: Start a program
6. Program: `python`
7. Arguments: `"C:\path\to\error_alert_system.py"`
8. Add environment variable: `EMAIL_PASSWORD=your-password`

### Option 2: Run on VM (Recommended)

**Upload script to VM:**
```bash
gcloud compute scp error_alert_system.py inventory-updater-vm:/home/banzo/ --zone=us-central1-a
```

**Add to VM cron:**
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a

# Edit crontab
crontab -e

# Add this line (runs every 15 minutes):
*/15 * * * * cd /home/banzo && export EMAIL_PASSWORD='your-password' && python3 error_alert_system.py >> error_alerts.log 2>&1
```

---

## 🔔 What Triggers Alerts?

The system sends alerts when:

1. **Cron job not configured** - Script won't run automatically
2. **Script not running** - No successful runs in last 15 minutes
3. **Errors detected** - Recent errors found in logs
4. **Column detection failed** - Can't detect Google Sheet columns

---

## 📧 Email Content

Alerts include:
- ✅ Status summary (cron, last run, columns)
- 🚨 Recent errors with timestamps
- 📋 Quick action commands
- 🔗 Links to troubleshooting guide

---

## 🛠️ Troubleshooting

### Email Not Sending?

1. **Check App Password:**
   - Must be 16 characters
   - No spaces
   - Generated from: https://myaccount.google.com/apppasswords

2. **Check Environment Variable:**
   ```bash
   echo $EMAIL_PASSWORD  # Linux/Mac
   echo %EMAIL_PASSWORD%  # Windows CMD
   ```

3. **Test Email Manually:**
   ```python
   from error_alert_system import send_email
   send_email("Test", "Test message")
   ```

### Too Many Emails?

The system only sends alerts when:
- New errors appear
- System status changes
- Critical issues detected

It won't spam you with the same error repeatedly.

---

## ⚙️ Configuration

Edit `error_alert_system.py` to customize:

- **Check interval**: How often to check logs
- **Alert thresholds**: What counts as an error
- **Email format**: Plain text or HTML
- **Recipients**: Who receives alerts

---

## 📊 Monitoring Schedule

**Recommended:**
- **Every 15 minutes**: Quick status check
- **Every hour**: Detailed log analysis
- **Daily**: Full system health report

---

## 🔒 Security Notes

- **App Password**: Never commit to git or share
- **Environment Variable**: Store securely
- **VM Access**: Use GCP IAM for secure access

---

## ✅ Verification

After setup, verify:

1. **Test email sent:**
   ```bash
   python error_alert_system.py
   ```

2. **Check email received:**
   - Check your inbox
   - Check spam folder

3. **Verify cron (if on VM):**
   ```bash
   gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="crontab -l"
   ```

---

**Last Updated:** November 5, 2025

