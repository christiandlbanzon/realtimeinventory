#!/usr/bin/env python3
"""
Clean sheets: remove non-cookie columns and duplicate columns.
- Mall PARs: latest tab
- Drunken Cookies: all store tabs
"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', 'service-account-key.json')

# Import from main updater
from vm_inventory_updater_fixed import _is_non_cookie_by_name


def normalize_header(h):
    """Normalize header for duplicate detection."""
    if not h or not isinstance(h, str):
        return ""
    return " ".join(h.lower().strip().split())


def get_columns_to_delete(headers, start_col=1):
    """
    Return list of column indices to delete (0-based from start_col).
    - Non-cookie columns
    - Duplicate columns (keep first occurrence)
    Returns indices to delete, sorted descending (for right-to-left deletion).
    """
    to_delete = []
    seen_normalized = {}
    for i, h in enumerate(headers):
        col_idx = start_col + i
        if not h or str(h).strip() == "":
            continue
        header_str = str(h).strip()
        norm = normalize_header(header_str)
        if not norm:
            continue
        # Non-cookie?
        if _is_non_cookie_by_name(header_str):
            to_delete.append(col_idx)
            continue
        # Duplicate?
        if norm in seen_normalized:
            to_delete.append(col_idx)  # Delete duplicate, keep first
            continue
        seen_normalized[norm] = col_idx
    return sorted(to_delete, reverse=True)  # Right to left


def clean_mall_pars(service, sheet_id, sheet_tab, dry_run=False):
    """Clean Mall PARs tab - remove non-cookie and duplicate columns."""
    meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_id_num = None
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == sheet_tab:
            sheet_id_num = s["properties"]["sheetId"]
            break
    if sheet_id_num is None:
        print(f"  Tab {sheet_tab} not found")
        return 0
    # Row 2 = headers (row 1 is locations)
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"'{sheet_tab}'!2:2"
    ).execute()
    headers = (result.get("values") or [[]])[0]
    # Pad to match column count
    while len(headers) < 100:
        headers.append("")
    cols_to_delete = get_columns_to_delete(headers, start_col=1)
    if not cols_to_delete:
        print(f"  No columns to remove")
        return 0
    print(f"  Removing {len(cols_to_delete)} columns: ", end="")
    removed_names = [headers[c - 1] if c <= len(headers) else "?" for c in cols_to_delete]
    print(", ".join(str(n)[:25] for n in removed_names[:10]))
    if len(removed_names) > 10:
        print(f"  ... and {len(removed_names) - 10} more")
    requests = []
    for col_idx in cols_to_delete:
        requests.append({
            "deleteDimension": {
                "range": {
                    "sheetId": sheet_id_num,
                    "dimension": "COLUMNS",
                    "startIndex": col_idx,
                    "endIndex": col_idx + 1,
                }
            }
        })
    if dry_run:
        return len(cols_to_delete)
    # Batch in chunks of 10 to avoid request size limits
    for i in range(0, len(requests), 10):
        chunk = requests[i : i + 10]
        service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": chunk},
        ).execute()
    return len(cols_to_delete)


def clean_drunken_cookies_tab(service, sheet_id, tab_name, dry_run=False):
    """Clean one Drunken Cookies tab."""
    meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_id_num = None
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == tab_name:
            sheet_id_num = s["properties"]["sheetId"]
            break
    if sheet_id_num is None:
        return 0
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"'{tab_name}'!1:1",
    ).execute()
    headers = (result.get("values") or [[]])[0]
    while len(headers) < 100:
        headers.append("")
    # Column 0 = Date, skip it
    cols_to_delete = get_columns_to_delete(headers[1:], start_col=1)
    if not cols_to_delete:
        return 0
    print(f"  {tab_name}: removing {len(cols_to_delete)} columns")
    requests = []
    for col_idx in cols_to_delete:
        requests.append({
            "deleteDimension": {
                "range": {
                    "sheetId": sheet_id_num,
                    "dimension": "COLUMNS",
                    "startIndex": col_idx,
                    "endIndex": col_idx + 1,
                }
            }
        })
    if dry_run:
        return len(cols_to_delete)
    for i in range(0, len(requests), 10):
        chunk = requests[i : i + 10]
        service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": chunk},
        ).execute()
    return len(cols_to_delete)


def main():
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    print("=" * 60)
    print("CLEAN SHEETS - Remove non-cookies and duplicates")
    if dry_run:
        print("(DRY RUN - no changes will be made)")
    print("=" * 60)

    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_service_account_file(
        "service-account-key.json",
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
    )
    service = build("sheets", "v4", credentials=creds)

    # Mall PARs has different structure (location columns, not cookie-name columns) - skip column cleanup.
    # Non-cookie ROWS in Mall PARs are cleared by vm_inventory_updater each run.

    # Drunken Cookies - all tabs (has cookie names as column headers)
    print("\n[1] Drunken Cookies sheet")
    DRUNKEN_COOKIES_SHEET_ID = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"
    meta = service.spreadsheets().get(spreadsheetId=DRUNKEN_COOKIES_SHEET_ID).execute()
    dc_tabs = [s["properties"]["title"] for s in meta.get("sheets", [])]
    total_dc = 0
    for tab in dc_tabs:
        n = clean_drunken_cookies_tab(service, DRUNKEN_COOKIES_SHEET_ID, tab, dry_run=dry_run)
        total_dc += n
    print(f"  Total {'would remove' if dry_run else 'removed'} from Drunken Cookies: {total_dc} columns")

    print("\n" + "=" * 60)
    print("Done")
    print("=" * 60)


if __name__ == "__main__":
    main()
