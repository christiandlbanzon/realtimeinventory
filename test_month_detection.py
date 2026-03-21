#!/usr/bin/env python3
"""Test month detection for sheet switching"""

from datetime import datetime
from zoneinfo import ZoneInfo

tz = ZoneInfo("America/Puerto_Rico")
now = datetime.now(tz)
current_month = now.month

print("="*80)
print("MONTH DETECTION TEST")
print("="*80)
print(f"\nCurrent Date: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"Current Month: {current_month}")

if current_month >= 2:
    sheet_id = "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4"
    sheet_name = "February sheet"
else:
    sheet_id = "1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE"
    sheet_name = "January sheet"

print(f"\n✅ Will use: {sheet_name}")
print(f"   Sheet ID: {sheet_id}")

if current_month >= 2:
    print("\n✅ February+ detected - Using February sheet automatically!")
else:
    print("\n📅 January detected - Using January sheet")
