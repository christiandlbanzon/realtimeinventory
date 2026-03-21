# Reinstall gcloud CLI - Clean Fix

## Why Reinstall?
Your current gcloud installation has permission issues and environment variable conflicts that are blocking all operations. A fresh install will:
- ✅ Create new config files with proper permissions
- ✅ Fix environment variable conflicts
- ✅ Give you reliable access to the VM

## Steps (Takes ~5 minutes)

### 1. Uninstall Current gcloud
- Open **Settings** → **Apps** → **Apps & features**
- Search for "Google Cloud SDK"
- Click **Uninstall**

### 2. Delete Old Config (Important!)
- Open File Explorer
- Go to: `C:\Users\banzo\AppData\Roaming\gcloud`
- **Delete the entire `gcloud` folder** (this removes corrupted config)

### 3. Reinstall gcloud
- Download installer: https://cloud.google.com/sdk/docs/install
- Run the installer
- Accept defaults (or customize if you prefer)
- **Important**: When prompted, choose "Run gcloud init" (or we'll do it manually)

### 4. Authenticate
Open a **NEW PowerShell window** and run:

```powershell
cd "e:\prog fold\Drunken cookies\real-time-inventory"
gcloud auth activate-service-account --key-file=service-account-key.json
gcloud config set project boxwood-chassis-332307
```

### 5. Apply VM Fix
```powershell
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && python3 apply_fix_on_vm.py"
```

## Expected Result
✅ Fix script runs on VM
✅ Promotion items (like Biscoff) will be counted correctly going forward
✅ All future updates will work properly

---

## Alternative: Manual SSH (If reinstall seems too much)
If you want to avoid reinstall, you can manually SSH:
1. Open a **completely fresh** PowerShell window (close all existing ones)
2. Run: `gcloud compute ssh inventory-updater-vm --zone=us-central1-a`
3. Once connected to VM:
   ```bash
   cd /home/banzo
   python3 apply_fix_on_vm.py
   ```

But honestly, **reinstall is cleaner and more reliable** for long-term use.
