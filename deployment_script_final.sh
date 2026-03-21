#!/bin/bash
set -e
exec > /var/log/deploy.log 2>&1
echo "=== Deployment Started ==="
date

# Create user
if ! id -u banzo &>/dev/null; then
    useradd -m -s /bin/bash banzo
fi

mkdir -p /home/banzo
chown -R banzo:banzo /home/banzo

# Install dependencies
apt-get update -y
apt-get install -y python3 python3-pip git
pip3 install --upgrade pip
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests python-dotenv fuzzywuzzy python-Levenshtein

# Switch to banzo user and deploy files
su - banzo << 'DEPLOYFILES'
cd /home/banzo

# Deploy vm_inventory_updater.py
cat > /home/banzo/vm_inventory_updater.py << 'ENDOFFILE1'