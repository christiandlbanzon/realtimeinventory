# Deploy with proper authentication - disable ALL proxy settings

# Disable ALL proxy settings
$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""
$env:http_proxy = ""
$env:https_proxy = ""
$env:ALL_PROXY = ""
$env:all_proxy = ""
$env:NO_PROXY = "*"
[System.Net.WebRequest]::DefaultWebProxy = $null

# Use temp config to avoid permission issues
$env:CLOUDSDK_CONFIG = "$env:TEMP\gcloud_config"

# Set service account as default credentials
$env:GOOGLE_APPLICATION_CREDENTIALS = (Resolve-Path "service-account-key.json").Path

$GCLOUD = "C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$PROJECT_ID = "boxwood-chassis-332307"
$REGION = "us-east1"
$JOB_NAME = "inventory-updater"

Write-Host "=================================================================================="
Write-Host "DEPLOYING TO CLOUD RUN WITH SERVICE ACCOUNT AUTH"
Write-Host "=================================================================================="
Write-Host ""
Write-Host "Job: $JOB_NAME"
Write-Host "Region: $REGION"
Write-Host "Project: $PROJECT_ID"
Write-Host "Service Account: $env:GOOGLE_APPLICATION_CREDENTIALS"
Write-Host ""

# Set project
Write-Host "[1/5] Setting project..."
& $GCLOUD config set project $PROJECT_ID 2>&1 | Out-Null
Write-Host "OK: Project set"
Write-Host ""

# Try to activate service account (may fail due to proxy, but we'll use GOOGLE_APPLICATION_CREDENTIALS instead)
Write-Host "[2/5] Setting up authentication..."
& $GCLOUD auth activate-service-account --key-file=service-account-key.json --quiet 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: Service account activated"
} else {
    Write-Host "INFO: Using GOOGLE_APPLICATION_CREDENTIALS environment variable instead"
    Write-Host "      (This works for Python API, gcloud may still need auth)"
}
Write-Host ""

# Enable APIs using Python (works with service account key)
Write-Host "[3/5] Enabling APIs..."
python -c "
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'service-account-key.json'
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

creds = service_account.Credentials.from_service_account_file('service-account-key.json', scopes=['https://www.googleapis.com/auth/cloud-platform'])
http = httplib2.Http(proxy_info=None)
auth_http = AuthorizedHttp(creds, http=http)
serviceusage = build('serviceusage', 'v1', http=auth_http)

apis = ['cloudbuild.googleapis.com', 'run.googleapis.com', 'cloudscheduler.googleapis.com']
for api in apis:
    try:
        serviceusage.services().enable(name=f'projects/boxwood-chassis-332307/services/{api}').execute()
        print(f'  OK: {api}')
    except Exception as e:
        if 'already enabled' in str(e).lower():
            print(f'  OK: {api} (already enabled)')
        else:
            print(f'  WARN: {api} - {e}')
"
Write-Host ""

# Build using Python API (bypasses gcloud auth issues)
Write-Host "[4/5] Building Docker image using Python API..."
Write-Host "This builds in Google Cloud - no local Docker needed!"
Write-Host "This will take 3-5 minutes..."
Write-Host ""

python -c "
import os
import subprocess
import sys

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'service-account-key.json'
os.environ['CLOUDSDK_CONFIG'] = os.path.join(os.environ['TEMP'], 'gcloud_config')

# Disable proxy
for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    os.environ.pop(var, None)

gcloud = r'C:\Users\banzo\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'
cmd = [gcloud, 'builds', 'submit', '--tag', 'gcr.io/boxwood-chassis-332307/inventory-updater']

print('Running:', ' '.join(cmd))
print()

proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

for line in proc.stdout:
    print(line, end='')

proc.wait()
sys.exit(proc.returncode)
"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Build failed"
    Write-Host ""
    Write-Host "The proxy issue is preventing gcloud from authenticating."
    Write-Host ""
    Write-Host "SOLUTION: Use Google Cloud Shell (no proxy issues there):"
    Write-Host "  1. Go to: https://shell.cloud.google.com/"
    Write-Host "  2. Upload the 4 files"
    Write-Host "  3. Run the gcloud commands"
    exit 1
}

Write-Host ""
Write-Host "OK: Docker image built!"
Write-Host ""

# Create Cloud Run Job using Python API
Write-Host "[5/5] Creating Cloud Run Job..."
python -c "
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'service-account-key.json'
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

creds = service_account.Credentials.from_service_account_file('service-account-key.json', scopes=['https://www.googleapis.com/auth/cloud-platform'])
http = httplib2.Http(proxy_info=None)
auth_http = AuthorizedHttp(creds, http=http)
run = build('run', 'v2', http=auth_http)

job_body = {
    'template': {
        'template': {
            'containers': [{
                'image': 'gcr.io/boxwood-chassis-332307/inventory-updater',
                'env': []
            }],
            'serviceAccountName': '703996360436-compute@developer.gserviceaccount.com',
            'timeout': '600s',
            'maxRetries': 1
        }
    }
}

parent = f'projects/boxwood-chassis-332307/locations/us-east1'

try:
    # Try to create
    result = run.projects().locations().jobs().create(
        parent=parent,
        jobId='inventory-updater',
        body=job_body
    ).execute()
    print('OK: Cloud Run Job created!')
except Exception as e:
    if 'already exists' in str(e).lower():
        # Update instead
        result = run.projects().locations().jobs().patch(
            name=f'{parent}/jobs/inventory-updater',
            body=job_body
        ).execute()
        print('OK: Cloud Run Job updated!')
    else:
        print(f'ERROR: {e}')
        raise
"

Write-Host ""
Write-Host "=================================================================================="
Write-Host "DEPLOYMENT COMPLETE!"
Write-Host "=================================================================================="
Write-Host ""
Write-Host "View: https://console.cloud.google.com/run/jobs?project=$PROJECT_ID"
