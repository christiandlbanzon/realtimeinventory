#!/usr/bin/env python3
"""
Cloud Run Job: apply Clover Mall PARs roster (column A) **forward only** from the
**job run date** in America/Puerto_Rico (default: N=7 days). First tab = run day
(Friday 1am schedule → that Friday), then the next N−1 calendar days — **never**
earlier tabs. Each date uses that month’s Mall PARs spreadsheet (Drive lookup +
fallbacks in sync_roster_job).

Env:
  ROSTER_SYNC_DAYS   default 7 (ignored if ROSTER_SYNC_REST_OF_MONTH is set)
  ROSTER_SYNC_REST_OF_MONTH  set to 1/true: sync **today → last day of current month** in PR only
    (forward from run day; does **not** backfill from the 1st). Overrides ROSTER_SYNC_DAYS.
  FOR_DATE  optional YYYY-MM-DD anchor instead of “now” in PR (for tests / replays).
  SYNC_CLOVER_LOCATION  default VSJ
  SYNC_ROSTER_TARGETS   default mall_pars,dispatch_pars,morning_pars (order: 1 Mall, 2 Dispatch, 3 Morning)
  INVENTORY_SHEET_ID   not used — each day resolves its month’s sheet (required for Mar→Apr weeks).
  DISPATCH_PARS_SHEET_ID / MORNING_PARS_SHEET_ID  optional; set at month rollover when v2 file ids change.
"""
from __future__ import annotations

import calendar
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PR = ZoneInfo("America/Puerto_Rico")
DISPATCH_PARS_DEFAULT_SHEET_ID = "1XC9o3iGhv2YWAXZqnDwz0bxA1N4kJKkn_fswiz7X6ek"
MORNING_PARS_DEFAULT_SHEET_ID = "1BbZc3DYa3r0aCR2jiwm6ecs7cs7v4IRO39nHFIYR1oc"


def main() -> int:
    import sync_roster_job as sr

    for_date = os.getenv("FOR_DATE", "").strip()
    if for_date:
        try:
            run_date = datetime.strptime(for_date, "%Y-%m-%d").date()
        except ValueError:
            print("FOR_DATE must be YYYY-MM-DD", flush=True)
            return 1
    else:
        run_date = datetime.now(PR).date() + timedelta(days=1)

    rest_of_month = os.getenv("ROSTER_SYNC_REST_OF_MONTH", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if rest_of_month:
        last_d = calendar.monthrange(run_date.year, run_date.month)[1]
        month_end = run_date.replace(day=last_d)
        days = (month_end - run_date).days + 1
        mode = "rest of month (today -> last day of month, forward only)"
    else:
        days = int(os.getenv("ROSTER_SYNC_DAYS", "7"))
        mode = f"ROSTER_SYNC_DAYS={days}"
    if days < 1 or days > 31:
        print("Computed day count must be 1–31", flush=True)
        return 1

    loc = os.getenv("SYNC_CLOVER_LOCATION", "VSJ")
    targets = (
        os.getenv("SYNC_ROSTER_TARGETS", "mall_pars,dispatch_pars,morning_pars").strip()
        or "mall_pars,dispatch_pars,morning_pars"
    )
    end_date = run_date + timedelta(days=days - 1)
    print(
        f"Roster window ({mode}): {run_date} -> {end_date} ({days} day(s))",
        flush=True,
    )

    script = os.path.join(APP_DIR, "sync_cookie_roster_from_clover.py")
    failed: list[str] = []

    for i in range(days):
        d = run_date + timedelta(days=i)
        sheet_id = sr._resolve_mall_pars_sheet_id(d)
        tab = f"{d.month}-{d.day}"
        cmd = [
            sys.executable,
            script,
            "--location",
            loc,
            "--apply",
            "--targets",
            targets,
            "--mall-pars-sheet-id",
            sheet_id,
            "--mall-pars-tab",
            tab,
        ]
        ts = {t.strip().lower() for t in targets.split(",")}
        if "dispatch_pars" in ts:
            cmd.extend(
                [
                    "--dispatch-pars-sheet-id",
                    os.getenv("DISPATCH_PARS_SHEET_ID", DISPATCH_PARS_DEFAULT_SHEET_ID),
                    "--dispatch-pars-tab",
                    tab,
                ]
            )
        if "morning_pars" in ts:
            cmd.extend(
                [
                    "--morning-pars-sheet-id",
                    os.getenv("MORNING_PARS_SHEET_ID", MORNING_PARS_DEFAULT_SHEET_ID),
                    "--morning-pars-tab",
                    tab,
                ]
            )
        print(f"Week roster: {tab} sheet={sheet_id[:12]}…", flush=True)
        r = subprocess.call(cmd, cwd=APP_DIR)
        if r != 0:
            failed.append(tab)
        # Throttle between tabs to stay under Sheets API 60 reads/min/user quota
        if i < days - 1:
            time.sleep(15)

    print("Done. Failed tabs:", failed if failed else "none", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
