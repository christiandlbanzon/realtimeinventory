#!/usr/bin/env python3
"""
Verify Drunken Cookies sheet data against Clover API.
Compares totals per location per date - flags discrepancies.
"""

import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', 'service-account-key.json')

from vm_inventory_updater_fixed import load_credentials, fetch_sales_data

DRUNKEN_COOKIES_SHEET_ID = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"
LOC_TO_TAB = {
    "Plaza": "Plaza", "PlazaSol": "PlazaSol", "San Patricio": "San Patricio",
    "VSJ": "VSJ", "Montehiedra": "Montehiedra", "Plaza Carolina": "Plaza Carolina",
}


def get_dc_totals_for_date(service, date_str):
    """Get Drunken Cookies row totals per tab for a date."""
    totals = {}
    for loc, tab in LOC_TO_TAB.items():
        try:
            col_a = service.spreadsheets().values().get(
                spreadsheetId=DRUNKEN_COOKIES_SHEET_ID,
                range=f"'{tab}'!A:A",
            ).execute()
            rows = col_a.get("values") or []
            for i, row in enumerate(rows):
                if row and str(row[0]).strip() == date_str:
                    # Get full row (B onwards)
                    row_num = i + 1
                    row_data = service.spreadsheets().values().get(
                        spreadsheetId=DRUNKEN_COOKIES_SHEET_ID,
                        range=f"'{tab}'!B{row_num}:ZZ{row_num}",
                    ).execute()
                    vals = (row_data.get("values") or [[]])[0]
                    total = sum(int(v) for v in vals if str(v).strip().isdigit())
                    totals[loc] = total
                    break
            else:
                totals[loc] = None  # Date not found
        except Exception as e:
            totals[loc] = f"Error: {e}"
    return totals


def main():
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    print("=" * 60)
    print("VERIFY Drunken Cookies vs Clover")
    print("=" * 60)

    creds = Credentials.from_service_account_file(
        "service-account-key.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    service = build("sheets", "v4", credentials=creds)

    clover_creds, shopify_creds = load_credentials()
    tz = ZoneInfo("America/Puerto_Rico")
    today = datetime.now(tz).date()

    # Check last 7 days
    issues = []
    for d in range(7):
        target_date = today - timedelta(days=d)
        date_str = target_date.strftime("%Y-%m-%d")
        target_dt = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=tz)

        sales_data = fetch_sales_data(clover_creds, shopify_creds, target_dt)
        dc_totals = get_dc_totals_for_date(service, date_str)

        for loc in LOC_TO_TAB:
            if loc not in sales_data:
                continue
            clover_total = sum(sales_data[loc].values())
            dc_val = dc_totals.get(loc)
            if dc_val is None:
                issues.append(f"{date_str} {loc}: MISSING in Drunken Cookies")
            elif isinstance(dc_val, str):
                issues.append(f"{date_str} {loc}: {dc_val}")
            elif abs(dc_val - clover_total) > 2:
                issues.append(f"{date_str} {loc}: DC={dc_val} vs Clover={clover_total} (diff={dc_val - clover_total})")

    if issues:
        print("\nIssues found:")
        for i in issues[:20]:
            print(f"  {i}")
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more")
    else:
        print("\nNo major discrepancies found.")
    print()


if __name__ == "__main__":
    main()
