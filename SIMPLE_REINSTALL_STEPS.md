# Simple gcloud Reinstall - 5 Minutes

## The Problem
gcloud can't write to `credentials.db` due to permission issues. A fresh install fixes this.

## Quick Steps

### 1. Uninstall (1 minute)
- Press `Win + I` (Settings)
- Go to **Apps** → **Apps & features**
- Search for **"Google Cloud SDK"**
- Click **Uninstall**

### 2. Delete Config (30 seconds)
- Press `Win + R`
- Type: `%APPDATA%\gcloud`
- Press Enter
- **Delete the entire `gcloud` folder**

### 3. Reinstall (2 minutes)
- Go to: https://cloud.google.com/sdk/docs/install
- Download the Windows installer
- Run it and accept defaults

### 4. Run Fix (30 seconds)
After reinstall, open a **NEW PowerShell window** and run:

```powershell
cd "e:\prog fold\Drunken cookies\real-time-inventory"
.\auto_fix_after_reinstall.ps1
```

OR manually:
```powershell
gcloud auth activate-service-account --key-file=service-account-key.json
gcloud config set project boxwood-chassis-332307
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && python3 apply_fix_on_vm.py"
```

## That's It!
✅ Fix will be applied to VM
✅ Promotion items will count correctly going forward
