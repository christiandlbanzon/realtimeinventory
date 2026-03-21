#!/usr/bin/env python3
"""
Backfill missing data for both primary inventory sheet and Drunken Cookies sheet.
Runs the inventory updater for each date in the range with FOR_DATE (fetches
Clover/Shopify sales and writes to both sheets).

Usage:
  python backfill_drunken_cookies.py                    # last 30 days (default)
  python backfill_drunken_cookies.py 2025-12-01 2025-12-29
  python backfill_drunken_cookies.py --dry-run 2025-12-01 2025-12-29

Requires (in real-time-inventory/):
  - vm_inventory_updater_fixed.py
  - clover_creds.json
  - service-account-key.json

The Drunken Cookies sheet must be shared with the service account email
(from service-account-key.json) as Editor, or writes to that sheet will fail
(you may only see a warning in the log).
Run this script locally (same machine/VM that has the keys and sheet access).
"""

import os
import sys
import subprocess
import codecs
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Puerto_Rico")
SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vm_inventory_updater_fixed.py")

# Default backfill window when VM/job stopped (adjust if you need more)
DEFAULT_BACKFILL_DAYS = 30


def backfill_date(target_date, dry_run: bool = False):
    """Run updater for a single date."""
    date_str = target_date.strftime("%Y-%m-%d")
    if dry_run:
        print(f"  [DRY-RUN] Would backfill {date_str}")
        return True
    env = os.environ.copy()
    env["FOR_DATE"] = date_str
    print(f"  Backfilling {date_str}...", end=" ", flush=True)
    try:
        # Set UTF-8 encoding for Windows compatibility (avoids UnicodeEncodeError on emoji)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        result = subprocess.run(
            [sys.executable, SCRIPT_PATH],
            env=env,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=600,  # Increased timeout for API calls
        )
        if result.returncode == 0:
            print("OK")
            return True
        else:
            print(f"FAILED (exit {result.returncode})")
            if result.stderr:
                for line in result.stderr.strip().split("\n")[-5:]:
                    print(f"    {line}")
            return False
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    print("=" * 60)
    print("BACKFILL - Primary sheet + Drunken Cookies sheet")
    print("=" * 60)

    today = datetime.now(TZ).date()
    # Default: last 30 days (excluding today) so you can backfill after VM stopped
    start_date = today - timedelta(days=DEFAULT_BACKFILL_DAYS)
    end_date = today - timedelta(days=1)  # yesterday

    if len(args) >= 1:
        try:
            start_date = datetime.strptime(args[0], "%Y-%m-%d").date()
        except ValueError:
            print(f"Invalid start date: {args[0]}. Use YYYY-MM-DD")
            print("Usage: python backfill_drunken_cookies.py [start_date] [end_date] [--dry-run]")
            sys.exit(1)
    if len(args) >= 2:
        try:
            end_date = datetime.strptime(args[1], "%Y-%m-%d").date()
        except ValueError:
            print(f"Invalid end date: {args[1]}. Use YYYY-MM-DD")
            sys.exit(1)

    if start_date > end_date:
        print("Error: start_date must be <= end_date")
        sys.exit(1)

    dates = []
    d = start_date
    while d <= end_date:
        dates.append(d)
        d += timedelta(days=1)

    print(f"\nDates to backfill: {len(dates)}")
    print(f"  From: {start_date}")
    print(f"  To:   {end_date}")
    print(f"  Script: {SCRIPT_PATH}")
    if dry_run:
        print("  Mode: DRY-RUN (no writes)")
    print()

    success = 0
    failed = 0
    for target_date in dates:
        if backfill_date(target_date, dry_run=dry_run):
            success += 1
        else:
            failed += 1

    print()
    print("=" * 60)
    print(f"Done: {success} OK, {failed} failed")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
