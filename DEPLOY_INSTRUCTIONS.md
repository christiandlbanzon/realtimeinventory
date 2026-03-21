# 🚀 Quick Deployment Instructions

## Issue: Permission Error

gcloud needs write permissions to store credentials. You have two options:

## Option 1: Run PowerShell as Administrator (Recommended)

1. **Right-click PowerShell** → **Run as Administrator**
2. Navigate to project directory:
   ```powershell
   cd "e:\prog fold\Drunken cookies\real-time-inventory"
   ```
3. Run the deployment script:
   ```powershell
   .\deploy_vm.ps1
   ```

## Option 2: Fix Permissions Manually

1. **Right-click** on `C:\Users\banzo\AppData\Roaming\gcloud` folder
2. Select **Properties** → **Security** tab
3. Click **Edit** → **Add** → Type your username → **OK**
4. Check **Full control** → **OK**
5. Then run:
   ```powershell
   cd "e:\prog fold\Drunken cookies\real-time-inventory"
   python deploy_to_new_vm.py
   ```

## Option 3: Authenticate First (Manual)

1. Open PowerShell (can be regular, not admin)
2. Run:
   ```powershell
   & "C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" auth login
   ```
3. Complete authentication in browser
4. Then run:
   ```powershell
   cd "e:\prog fold\Drunken cookies\real-time-inventory"
   python deploy_to_new_vm.py
   ```

## What Will Happen

The deployment will:
1. ✅ Create VM named `real-time-inventory`
2. ✅ Upload all required files
3. ✅ Set up Python environment
4. ✅ Install dependencies
5. ✅ Configure cron job (runs every 5 minutes)
6. ✅ Verify deployment

## After Deployment

Check logs:
```powershell
gcloud compute ssh banzo@real-time-inventory --zone=us-central1-a --command="tail -50 ~/inventory_cron.log"
```

Test manually:
```powershell
gcloud compute ssh banzo@real-time-inventory --zone=us-central1-a --command="cd ~ && ~/venv/bin/python ~/vm_inventory_updater.py"
```
