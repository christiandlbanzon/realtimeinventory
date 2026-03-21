FROM python:3.12-slim

WORKDIR /app

# Copy credentials
COPY clover_creds.json .
COPY service-account-key.json .

# Copy main script
COPY vm_inventory_updater_fixed.py vm_inventory_updater.py

# Install dependencies
RUN pip install --no-cache-dir \
    google-auth \
    google-auth-oauthlib \
    google-auth-httplib2 \
    google-api-python-client \
    requests \
    python-dotenv \
    fuzzywuzzy \
    python-Levenshtein

# Set environment variable for service account
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json

# Run the script
CMD ["python", "vm_inventory_updater.py"]
