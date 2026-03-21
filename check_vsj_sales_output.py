"""Check what fetch_clover_sales returns for VSJ"""

import os
import sys
import codecs
os.environ['FOR_DATE'] = '2026-02-15'

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from vm_inventory_updater_fixed import load_credentials, fetch_clover_sales
from datetime import datetime
from zoneinfo import ZoneInfo

creds_result = load_credentials()
clover_creds, _ = creds_result if isinstance(creds_result, tuple) else (creds_result, None)
vsj_creds = clover_creds.get('VSJ')

tz = ZoneInfo('America/Puerto_Rico')
target_date = datetime(2026, 2, 15, 0, 0, 0, 0, tz)

print("Fetching VSJ sales...")
sales = fetch_clover_sales(vsj_creds, target_date)

print(f"\nVSJ Cookie Sales (total: {len(sales)} cookies):")
print(f"F - Brookie: {sales.get('F - Brookie', 0)}")
print(f"G - Cornbread with Dulce de Leche: {sales.get('G - Cornbread with Dulce de Leche', 0)}")
print(f"Cherry Red Velvet Cake: {sales.get('Cherry Red Velvet Cake', 0)}")

# Show all Brookie-related keys
print(f"\nAll Brookie-related keys:")
for k, v in sorted(sales.items()):
    if 'brookie' in k.lower():
        print(f"  '{k}': {v}")

print(f"\nAll cookie keys:")
for k, v in sorted(sales.items()):
    print(f"  '{k}': {v}")
