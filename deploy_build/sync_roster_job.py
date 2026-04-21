#!/usr/bin/env python3
"""
Cloud Run Job entrypoint: Clover → Mall PARs column A (and optionally Drunken row 1).

Default: Mall PARs + Dispatch PARs + Morning PARs (order 1→2→3). New flavors on Drunken Cookies are handled
by vm_inventory_updater (appends new columns on row 1 + values); running --targets drunken overwrites row 1
with fixed A–N slots — opt in with SYNC_ROSTER_TARGETS=drunken,...

For **weekly** Friday ~1am (menu set for the week), prefer `sync_roster_week_job.py` + Cloud Scheduler
(`create_roster_weekly_scheduler.py`; see module docstrings).

SYNC_CLOVER_LOCATION (default VSJ), optional FOR_DATE, optional SYNC_ROSTER_TARGETS (default:
``mall_pars,dispatch_pars,morning_pars``). At month rollover set ``DISPATCH_PARS_SHEET_ID`` and
``MORNING_PARS_SHEET_ID`` to the new v2 files (Mall PARs uses Drive lookup / ``INVENTORY_SHEET_ID``).
"""
from __future__ import annotations

import os
import subprocess
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Same default as sync_cookie_roster_from_clover.DISPATCH_PARS_DEFAULT_SHEET_ID (avoid import cycle).
DISPATCH_PARS_DEFAULT_SHEET_ID = "1XC9o3iGhv2YWAXZqnDwz0bxA1N4kJKkn_fswiz7X6ek"
MORNING_PARS_DEFAULT_SHEET_ID = "1BbZc3DYa3r0aCR2jiwm6ecs7cs7v4IRO39nHFIYR1oc"


def _import_viu():
    try:
        import vm_inventory_updater_fixed as viu
    except ImportError:
        import vm_inventory_updater as viu
    return viu


def _resolve_mall_pars_sheet_id(d) -> str:
    from google.oauth2.service_account import Credentials

    viu = _import_viu()
    creds = Credentials.from_service_account_file(
        os.path.join(APP_DIR, "service-account-key.json"),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
    )
    PARS_FOLDER_ID = "1CdAyO-8TGYJKgPs_8dSo0dFOX9ojCnC2"
    sid = viu._get_sheet_id_from_folder(creds, PARS_FOLDER_ID, d.month)
    if sid:
        return sid
    month = d.month
    if month == 1:
        return "1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE"
    if month == 2:
        return "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4"
    if month == 3:
        return "1kYbyeLoOd986lZrnc57XOynanYLbW2NM2fwypUJa2PQ"
    if month == 4:
        return "1C5_N8oHds9Xw9pqN5PptGAVHJ2WeKrh35PCiejusl88"  # April Mall PARs_2026
    return "1kYbyeLoOd986lZrnc57XOynanYLbW2NM2fwypUJa2PQ"


def main() -> int:
    """
    Mall PARs / Drunken header tab = M-D for the *calendar* day in Puerto Rico (today),
    not inventory's early-morning "yesterday" rule — at 1 AM on 3/27 we want tab 3-27.
    Override with FOR_DATE=YYYY-MM-DD when needed.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    for_date = os.getenv("FOR_DATE")
    if for_date:
        try:
            d = datetime.strptime(for_date, "%Y-%m-%d").date()
        except ValueError:
            d = datetime.now(ZoneInfo("America/Puerto_Rico")).date()
    else:
        d = datetime.now(ZoneInfo("America/Puerto_Rico")).date()

    tab = f"{d.month}-{d.day}"
    sheet_id = os.getenv("INVENTORY_SHEET_ID") or _resolve_mall_pars_sheet_id(d)
    loc = os.getenv("SYNC_CLOVER_LOCATION", "VSJ")
    # Mall PARs = fixed A–N labels in column A (primary). Drunken = optional; inventory job
    # already appends new flavor columns — only add "drunken" if you want row 1 reset to A–N.
    targets = os.getenv("SYNC_ROSTER_TARGETS", "mall_pars,dispatch_pars").strip() or "mall_pars,dispatch_pars"
    env = os.environ.copy()

    cmd = [
        sys.executable,
        os.path.join(APP_DIR, "sync_cookie_roster_from_clover.py"),
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
    print("Roster sync:", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=APP_DIR, env=env)


if __name__ == "__main__":
    sys.exit(main())
