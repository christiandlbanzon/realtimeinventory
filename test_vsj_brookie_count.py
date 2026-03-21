import sys
import codecs
from vm_inventory_updater_fixed import fetch_clover_sales, load_credentials
from datetime import datetime
from zoneinfo import ZoneInfo

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

creds_result = load_credentials()
if isinstance(creds_result, tuple):
    clover_creds, _ = creds_result
else:
    clover_creds = creds_result

vsj_creds = clover_creds.get('VSJ')
tz = ZoneInfo('America/Puerto_Rico')
target = datetime(2026, 2, 15, 0, 0, 0, 0, tz)

sales = fetch_clover_sales(vsj_creds, target)
brookie = sales.get('F - Brookie', 0)

print(f"VSJ Brookie count: {brookie}")
print(f"Expected (Clover site): 123")
print(f"Difference: {123 - brookie}")
