FROM python:3.12-slim

WORKDIR /app

# Copy credentials
COPY clover_creds.json .
COPY service-account-key.json .

# Copy main script (fixed version -> vm_inventory_updater.py for compat)
COPY vm_inventory_updater_fixed.py vm_inventory_updater.py
COPY sync_cookie_roster_from_clover.py .
COPY sync_roster_job.py .
COPY sync_roster_week_job.py .

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

# Set environment variable
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json

# Inventory updater default; weekly roster: python sync_roster_week_job.py (single day: sync_roster_job.py)
CMD ["python", "vm_inventory_updater.py"]
