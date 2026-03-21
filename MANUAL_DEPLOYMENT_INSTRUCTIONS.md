# Manual Deployment Instructions

Your VM `real-time-inventory` is created and running in zone `us-central1-b`!

Since the API is having issues, here's how to deploy manually via SSH:

## Option 1: Use Google Cloud Console SSH (Easiest)

1. Go to: https://console.cloud.google.com/compute/instances?project=boxwood-chassis-332307
2. Find your VM: `real-time-inventory`
3. Click the "SSH" button next to it
4. This opens a browser-based SSH terminal

## Option 2: Use gcloud CLI (if permissions work)

```powershell
cd "e:\prog fold\Drunken cookies\real-time-inventory"
gcloud compute ssh real-time-inventory --zone=us-central1-b --project=boxwood-chassis-332307
```

## Once Connected via SSH:

Run these commands one by one:

```bash
# Create user and directory
sudo useradd -m -s /bin/bash banzo
sudo mkdir -p /home/banzo
sudo chown -R banzo:banzo /home/banzo

# Install dependencies
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip git
sudo pip3 install --upgrade pip
sudo pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests python-dotenv fuzzywuzzy python-Levenshtein

# Switch to banzo user
sudo su - banzo
cd /home/banzo
```

Then I'll provide you with commands to copy the files. Or wait a few minutes and I'll try the API again!
