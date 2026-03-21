#!/usr/bin/env python3
"""
Fix Drunken Cookies sheet: remove duplicate Brookie columns, add Brookie with Nutella.
Then backfill with correct data from Clover.

Usage:
  python fix_drunken_cookies_brookie.py                    # fix structure + backfill last 30 days
  python fix_drunken_cookies_brookie.py --fix-only         # only fix structure, no backfill
  python fix_drunken_cookies_brookie.py 2025-12-01 2026-01-29  # backfill date range
"""

import os
import sys
import subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

DRUNKEN_COOKIES_SHEET_ID = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKFILL_SCRIPT = os.path.join(SCRIPT_DIR, "backfill_drunken_cookies.py")
UPDATER_SCRIPT = os.path.join(SCRIPT_DIR, "vm_inventory_updater_fixed.py")
TZ = ZoneInfo("America/Puerto_Rico")

LOC_TO_TAB = {
    "Plaza": "Plaza",
    "PlazaSol": "PlazaSol",
    "San Patricio": "San Patricio",
    "VSJ": "VSJ",
    "Montehiedra": "Montehiedra",
    "Plaza Carolina": "Plaza Carolina",
}


def _normalize(s):
    return " ".join((s or "").lower().split())


def fix_sheet_structure(service, dry_run=False):
    """Remove duplicate Brookie columns, add Brookie with Nutella if missing."""
    meta = service.spreadsheets().get(spreadsheetId=DRUNKEN_COOKIES_SHEET_ID).execute()
    sheets = meta.get("sheets", [])
    requests = []
    tab_updates = []

    for sheet_info in sheets:
        props = sheet_info["properties"]
        tab_title = props["title"]
        sheet_id = props["sheetId"]

        # Skip non-store tabs (e.g. External, Tab)
        if tab_title not in LOC_TO_TAB.values():
            continue

        # Read row 1
        result = service.spreadsheets().values().get(
            spreadsheetId=DRUNKEN_COOKIES_SHEET_ID, range=f"'{tab_title}'!1:1"
        ).execute()
        headers = (result.get("values") or [[]])[0]
        if not headers or headers[0] != "Date":
            print(f"  Skip '{tab_title}': no Date in A1")
            continue

        # Find duplicate Brookie columns (exact "brookie", not "brookie with nutella")
        brookie_indices = []
        brookie_nutella_idx = None
        for i, h in enumerate(headers[1:], start=1):  # i = 0-based column index (1 = col B)
            norm = _normalize(h)
            if norm == "brookie":
                brookie_indices.append(i)
            elif norm == "brookie with nutella":
                brookie_nutella_idx = i

        # Delete duplicate Brookie columns (keep first, delete rest, right to left)
        to_delete = sorted(brookie_indices[1:], reverse=True)  # skip first
        for col_idx in to_delete:
            if dry_run:
                print(f"  [DRY-RUN] Would delete column {col_idx} (duplicate Brookie) in '{tab_title}'")
            else:
                requests.append({
                    "deleteDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": col_idx,
                            "endIndex": col_idx + 1,
                        }
                    }
                })
            tab_updates.append(f"{tab_title}: removed duplicate Brookie col {col_idx}")

        # Add Brookie with Nutella if missing
        if brookie_nutella_idx is None:
            # Insert after first Brookie column (or at end if no Brookie); use 0-based indices
            insert_after = brookie_indices[0] if brookie_indices else len(headers) - 1
            insert_at = insert_after + 1  # 0-based index where new column will go

            if dry_run:
                print(f"  [DRY-RUN] Would insert 'Brookie with Nutella' at col {insert_at + 1} in '{tab_title}'")
            else:
                requests.append({
                    "insertDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": insert_at,
                            "endIndex": insert_at + 1,
                        }
                    }
                })
                tab_updates.append(f"{tab_title}: added Brookie with Nutella at col {insert_at + 1}")

                # Update header in new column (0-based index for column_to_letter)
                tab_updates.append((tab_title, insert_at, "Brookie with Nutella"))

    if requests and not dry_run:
        service.spreadsheets().batchUpdate(
            spreadsheetId=DRUNKEN_COOKIES_SHEET_ID, body={"requests": requests}
        ).execute()
        print("  Applied structure changes")

        # Write new headers for inserted columns
        sys.path.insert(0, SCRIPT_DIR)
        from vm_inventory_updater_fixed import column_to_letter
        for item in tab_updates:
            if isinstance(item, tuple):
                tab_name, col_idx, header_name = item
                range_str = f"'{tab_name}'!{column_to_letter(col_idx)}1"
                service.spreadsheets().values().update(
                    spreadsheetId=DRUNKEN_COOKIES_SHEET_ID,
                    range=range_str,
                    valueInputOption="USER_ENTERED",
                    body={"values": [[header_name]]},
                ).execute()
                print(f"  Set header '{header_name}' in {tab_name}")

    return True


def run_backfill(start_date, end_date, dry_run=False):
    """Run backfill_drunken_cookies.py for the date range."""
    args = [
        sys.executable,
        BACKFILL_SCRIPT,
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
    ]
    if dry_run:
        args.append("--dry-run")
    print(f"\nRunning backfill: {' '.join(args)}")
    result = subprocess.run(
        args,
        cwd=SCRIPT_DIR,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=3600,
    )
    return result.returncode == 0


def main():
    fix_only = "--fix-only" in sys.argv
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--") and a != "-n"]

    print("=" * 60)
    print("Fix Drunken Cookies: remove duplicate Brookie, add Brookie with Nutella")
    print("=" * 60)

    # Auth
    creds_path = os.path.join(SCRIPT_DIR, "service-account-key.json")
    if not os.path.exists(creds_path):
        print("ERROR: service-account-key.json not found")
        sys.exit(1)
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds)

    # Fix structure
    print("\n[1/2] Fixing sheet structure...")
    fix_sheet_structure(service, dry_run=dry_run)
    print("  Done.")

    if fix_only:
        print("\n[--fix-only] Skipping backfill.")
        sys.exit(0)

    # Backfill
    today = datetime.now(TZ).date()
    start_date = today - timedelta(days=30)
    end_date = today - timedelta(days=1)
    if len(args) >= 1:
        try:
            start_date = datetime.strptime(args[0], "%Y-%m-%d").date()
        except ValueError:
            print(f"Invalid start date: {args[0]}")
            sys.exit(1)
    if len(args) >= 2:
        try:
            end_date = datetime.strptime(args[1], "%Y-%m-%d").date()
        except ValueError:
            print(f"Invalid end date: {args[1]}")
            sys.exit(1)

    print(f"\n[2/2] Backfilling {start_date} to {end_date}...")
    if run_backfill(start_date, end_date, dry_run=dry_run):
        print("\nBackfill complete.")
    else:
        print("\nBackfill had failures.")
        sys.exit(1)


if __name__ == "__main__":
    main()
