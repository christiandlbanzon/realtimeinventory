# Deploy Files via Google Cloud Console SSH

## Step-by-Step Instructions

### Step 1: Open SSH Terminal
1. Go to: https://console.cloud.google.com/compute/instances?project=boxwood-chassis-332307
2. Find VM: `real-time-inventory`
3. Click the **SSH** button (opens browser-based terminal)

### Step 2: Set Up User and Directory
Run these commands in the SSH terminal:

```bash
# Create user if doesn't exist
sudo useradd -m -s /bin/bash banzo

# Create directory
sudo mkdir -p /home/banzo
sudo chown -R banzo:banzo /home/banzo

# Switch to banzo user
sudo su - banzo
cd /home/banzo
```

### Step 3: Install Dependencies
```bash
# Update system
sudo apt-get update -y

# Install Python and pip
sudo apt-get install -y python3 python3-pip git

# Install Python packages
pip3 install --upgrade pip
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests python-dotenv fuzzywuzzy python-Levenshtein
```

### Step 4: Create Files
I'll provide the file contents to paste. For now, create empty files:

```bash
touch /home/banzo/vm_inventory_updater.py
touch /home/banzo/clover_creds.json
touch /home/banzo/service-account-key.json
chmod +x /home/banzo/vm_inventory_updater.py
```

### Step 5: Copy File Contents
I'll provide the file contents next - you'll paste them into these files using `nano`:

```bash
nano /home/banzo/vm_inventory_updater.py
# Paste content, then Ctrl+X, Y, Enter to save

nano /home/banzo/clover_creds.json
# Paste content, then Ctrl+X, Y, Enter to save

nano /home/banzo/service-account-key.json
# Paste content, then Ctrl+X, Y, Enter to save
```

### Step 6: Set Up Cron Job
```bash
(crontab -l 2>/dev/null | grep -v "vm_inventory_updater.py"; echo "*/5 * * * * cd /home/banzo && /usr/bin/python3 /home/banzo/vm_inventory_updater.py >> /home/banzo/inventory_cron.log 2>&1") | crontab -

# Verify cron is set
crontab -l
```

### Step 7: Test Run
```bash
# Test the script manually
cd /home/banzo
python3 /home/banzo/vm_inventory_updater.py

# Check logs
tail -f /home/banzo/inventory_cron.log
```

## Alternative: Use File Upload Feature

If the SSH terminal has a file upload feature:
1. Look for "Upload file" or folder icon in the SSH terminal
2. Upload the three files directly
3. Then run Step 6 (cron setup)
