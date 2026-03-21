# 🚀 Deployment Guide: Real-Time Inventory Updater to GCP VM

This guide will help you deploy the Real-Time Inventory Updater application to a **new** GCP VM instance.

## 📋 Prerequisites

1. **Google Cloud SDK (gcloud CLI)** installed
   - Download from: https://cloud.google.com/sdk/docs/install
   - Verify: `gcloud --version`

2. **Authentication**
   ```bash
   gcloud auth login
   ```
   This will open a browser for you to authenticate with your Google account.

3. **Required Files** (must be in project directory):
   - ✅ `vm_inventory_updater_fixed.py` - Main application
   - ✅ `service-account-key.json` - Google Sheets API credentials
   - ✅ `clover_creds.json` - Clover API credentials
   - ✅ `requirements.txt` - Python dependencies
   - ⚠️ `secrets/shopify_creds.json` - Shopify credentials (optional)

## 🎯 Quick Deployment

### Option 1: Automated Deployment Script (Recommended)

```bash
python deploy_to_new_vm.py
```

This script will:
1. ✅ Check gcloud authentication
2. ✅ Verify GCP project configuration
3. ✅ Create a new VM instance (if needed)
4. ✅ Upload all required files
5. ✅ Set up Python virtual environment
6. ✅ Install all dependencies
7. ✅ Configure cron job (runs every 5 minutes)
8. ✅ Verify deployment

### Option 2: Manual Deployment

If you prefer manual control, follow these steps:

#### Step 1: Authenticate with gcloud
```bash
gcloud auth login
gcloud config set project boxwood-chassis-332307
```

#### Step 2: Create VM Instance
```bash
gcloud compute instances create inventory-updater-vm \
  --zone=us-central1-a \
  --machine-type=e2-micro \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB
```

#### Step 3: Wait for VM to be ready (30-60 seconds)

#### Step 4: Upload Files
```bash
# Upload main script
gcloud compute scp vm_inventory_updater_fixed.py banzo@inventory-updater-vm:~/vm_inventory_updater.py --zone=us-central1-a

# Upload credentials
gcloud compute scp service-account-key.json banzo@inventory-updater-vm:~/ --zone=us-central1-a
gcloud compute scp clover_creds.json banzo@inventory-updater-vm:~/ --zone=us-central1-a

# Upload requirements
gcloud compute scp requirements.txt banzo@inventory-updater-vm:~/ --zone=us-central1-a
```

#### Step 5: SSH into VM and Setup Environment
```bash
gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a
```

Once inside the VM:
```bash
# Update system
sudo apt-get update

# Install Python dependencies
sudo apt-get install -y python3 python3-pip python3-venv python3-dev build-essential

# Create virtual environment
python3 -m venv ~/venv

# Activate virtual environment
source ~/venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python packages
pip install -r ~/requirements.txt
```

#### Step 6: Setup Cron Job
```bash
# Edit crontab
crontab -e

# Add this line (runs every 5 minutes):
*/5 * * * * cd ~ && export INVENTORY_SHEET_ID=1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno && ~/venv/bin/python ~/vm_inventory_updater.py >> ~/inventory_cron.log 2>&1
```

#### Step 7: Test Run
```bash
cd ~
~/venv/bin/python ~/vm_inventory_updater.py
```

## 🔍 Verification

### Check VM Status
```bash
gcloud compute instances list
```

### View Logs
```bash
gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a --command='tail -50 ~/inventory_cron.log'
```

### Check Cron Job
```bash
gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a --command='crontab -l'
```

### Manual Test Run
```bash
gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a --command='cd ~ && ~/venv/bin/python ~/vm_inventory_updater.py'
```

## 📊 What the Application Does

The Real-Time Inventory Updater:
- 🔄 Fetches sales data from Clover and Shopify APIs
- 📝 Updates Google Sheets with "Sold as of NOW" columns
- ⏰ Runs automatically every 5 minutes via cron
- 📍 Supports multiple locations (Plaza, PlazaSol, San Patricio, VSJ, Montehiedra, Plaza Carolina)
- 🍪 Maps cookie names from APIs to inventory sheet names
- ✅ Validates data before writing to sheets

## 🛠️ Troubleshooting

### Issue: gcloud command not found
**Solution**: Install Google Cloud SDK from https://cloud.google.com/sdk/docs/install

### Issue: Authentication failed
**Solution**: Run `gcloud auth login` again

### Issue: VM creation failed (quota exceeded)
**Solution**: 
- Check your GCP project quotas
- Use a different zone: `--zone=us-east1-b`
- Use a smaller machine type: `--machine-type=e2-micro`

### Issue: File upload failed
**Solution**: 
- Check VM is running: `gcloud compute instances list`
- Verify file paths are correct
- Check SSH keys: `gcloud compute config-ssh`

### Issue: Python packages installation failed
**Solution**:
```bash
# SSH into VM and run:
sudo apt-get update
sudo apt-get install -y python3-dev build-essential
~/venv/bin/pip install --upgrade pip
~/venv/bin/pip install -r ~/requirements.txt
```

### Issue: Script runs but doesn't update sheets
**Solution**:
- Check service account key has access to Google Sheet
- Verify `INVENTORY_SHEET_ID` environment variable is set correctly
- Check logs: `tail -100 ~/inventory_cron.log`

## 📝 Configuration

### Environment Variables

You can set these environment variables in the cron job:

- `INVENTORY_SHEET_ID`: Google Sheet ID (default: auto-detected based on month)
- `FOR_DATE`: Override date for testing (format: YYYY-MM-DD)

Example cron with custom sheet ID:
```bash
*/5 * * * * cd ~ && export INVENTORY_SHEET_ID=YOUR_SHEET_ID && ~/venv/bin/python ~/vm_inventory_updater.py >> ~/inventory_cron.log 2>&1
```

### VM Configuration

Default settings:
- **Zone**: `us-central1-a`
- **Machine Type**: `e2-micro` (1 vCPU, 1GB RAM)
- **Disk**: 20GB standard persistent disk
- **OS**: Ubuntu 22.04 LTS

To change these, edit `deploy_to_new_vm.py` or use manual deployment.

## 🔐 Security Notes

1. **Service Account Key**: Keep `service-account-key.json` secure. Never commit it to public repositories.

2. **API Credentials**: `clover_creds.json` contains API tokens. Keep it secure.

3. **VM Access**: Use SSH keys for secure access. The deployment script handles this automatically.

4. **Firewall**: The VM is created with HTTP/HTTPS tags. Adjust firewall rules as needed.

## 📞 Support

If you encounter issues:
1. Check the logs: `~/inventory_cron.log`
2. Verify all files are uploaded correctly
3. Test the script manually: `~/venv/bin/python ~/vm_inventory_updater.py`
4. Check cron is running: `crontab -l`

## ✅ Success Checklist

After deployment, verify:
- [ ] VM instance is running
- [ ] All files are uploaded (`ls -la ~/`)
- [ ] Virtual environment exists (`test -d ~/venv`)
- [ ] Python packages installed (`~/venv/bin/pip list`)
- [ ] Cron job is configured (`crontab -l`)
- [ ] Test run succeeds (`~/venv/bin/python ~/vm_inventory_updater.py`)
- [ ] Logs are being created (`tail ~/inventory_cron.log`)

---

**Last Updated**: February 1, 2026
