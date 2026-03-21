#!/usr/bin/env python3
from datetime import datetime
from zoneinfo import ZoneInfo

tz = ZoneInfo('America/Puerto_Rico')
target = datetime(2026, 1, 17, 0, 0, 0, tzinfo=tz)
start_ms = int(target.timestamp() * 1000)
extended_start = start_ms - (8 * 60 * 60 * 1000)
end_ms = int(datetime(2026, 1, 17, 23, 59, 59, 999999, tzinfo=tz).timestamp() * 1000)
extended_end = end_ms + (4 * 60 * 60 * 1000)

print(f'Query range: {extended_start} to {extended_end}')
print(f'Jan 17 start UTC: {datetime.fromtimestamp(extended_start/1000, tz=ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")}')
print(f'Jan 17 end UTC: {datetime.fromtimestamp(extended_end/1000, tz=ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")}')
print(f'Jan 17 start PR: {datetime.fromtimestamp(extended_start/1000, tz=tz).strftime("%Y-%m-%d %H:%M:%S")}')
print(f'Jan 17 end PR: {datetime.fromtimestamp(extended_end/1000, tz=tz).strftime("%Y-%m-%d %H:%M:%S")}')
