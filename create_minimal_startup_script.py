#!/usr/bin/env python3
"""Create a minimal startup script - just installs deps, then we deploy files separately"""

import os

print("Creating minimal startup script...")

minimal_script = """#!/bin/bash
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
"""

output_file = "startup_script_minimal.sh"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(minimal_script)

size = os.path.getsize(output_file)
print(f"Created: {output_file}")
print(f"Size: {size:,} bytes ({size/1024:.1f} KB)")
print("\nThis minimal script only installs dependencies.")
print("Files will be deployed separately via SSH after VM is created.")
