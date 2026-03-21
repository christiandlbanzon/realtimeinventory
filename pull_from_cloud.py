#!/usr/bin/env python3
"""
Pull deployed code from cloud and update local files.
Uses the source archive in Cloud Storage (same one used by Cloud Build).
No Docker required.
"""

import os
import sys
import tarfile
import tempfile

# Disable proxy
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'service-account-key.json'

PROJECT_ID = "boxwood-chassis-332307"
BUCKET_NAME = f"{PROJECT_ID}_cloudbuild"
SOURCE_PREFIX = "source/"

def main():
    print("="*60)
    print("PULL DEPLOYED CODE FROM CLOUD")
    print("="*60)
    print(f"\nBucket: gs://{BUCKET_NAME}/")
    print(f"Source: {SOURCE_PREFIX}*.tar.gz\n")

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from google_auth_httplib2 import AuthorizedHttp
        import httplib2
    except ImportError as e:
        print(f"ERROR: Missing dependency: {e}")
        print("  Run: pip install google-auth google-auth-httplib2 google-api-python-client")
        sys.exit(1)

    # Authenticate
    print("[1/4] Authenticating...")
    try:
        credentials = service_account.Credentials.from_service_account_file(
            'service-account-key.json',
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        http = httplib2.Http(proxy_info=None, timeout=60)
        authorized_http = AuthorizedHttp(credentials, http=http)
        storage = build('storage', 'v1', http=authorized_http)
        print("  OK")
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    # List objects - get most recent source archive
    print("\n[2/4] Finding latest deployed source...")
    try:
        objects = storage.objects().list(
            bucket=BUCKET_NAME,
            prefix=SOURCE_PREFIX
        ).execute()
        items = objects.get('items', [])
        if not items:
            print("  No source archives found. Deploy first with: python deploy_python_build.py")
            sys.exit(1)
        # Sort by timeCreated (newest first)
        items.sort(key=lambda x: x.get('timeCreated', ''), reverse=True)
        latest = items[0]
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    object_name = latest['name']
    created = latest.get('timeCreated', 'unknown')
    print(f"  Found: {object_name}")
    print(f"  Created: {created}")

    # Download
    print("\n[3/4] Downloading archive...")
    try:
        import io
        from googleapiclient.http import MediaIoBaseDownload

        request = storage.objects().get_media(bucket=BUCKET_NAME, object=object_name)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"  {int(status.progress() * 100)}%")
        buf.seek(0)
        print("  OK")
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    # Extract and update local
    print("\n[4/4] Updating local vm_inventory_updater_fixed.py...")
    try:
        with tarfile.open(fileobj=buf, mode='r:gz') as tar:
            member = tar.getmember('vm_inventory_updater_fixed.py')
            f = tar.extractfile(member)
            cloud_content = f.read().decode('utf-8')

        local_path = 'vm_inventory_updater_fixed.py'
        with open(local_path, 'r', encoding='utf-8') as f:
            local_content = f.read()

        if cloud_content == local_content:
            print("  Local already matches cloud - no changes needed.")
            return

        # Backup local
        backup_path = local_path + '.local_backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(local_content)
        print(f"  Backed up local to {backup_path}")

        # Overwrite with cloud version
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(cloud_content)
        print(f"  Updated {local_path} from cloud")

        print("\n" + "="*60)
        print("DONE - Local now matches deployed code")
        print("="*60)
        print(f"\nBackup of previous local: {backup_path}")

    except KeyError:
        print("  ERROR: vm_inventory_updater_fixed.py not in archive")
        sys.exit(1)
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
