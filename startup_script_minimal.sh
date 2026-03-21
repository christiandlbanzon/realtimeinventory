#!/bin/bash
set -e
exec > /var/log/startup.log 2>&1
echo "=== Minimal Startup Script Started ==="
date

# Update system
apt-get update -y
apt-get install -y python3 python3-pip git curl

# Create user
if ! id -u banzo &>/dev/null; then
    useradd -m -s /bin/bash banzo
fi

mkdir -p /home/banzo
chown -R banzo:banzo /home/banzo

# Install Python dependencies
pip3 install --upgrade pip
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests python-dotenv fuzzywuzzy python-Levenshtein

echo "=== Dependencies Installed ==="
echo "Ready for file deployment"
date
