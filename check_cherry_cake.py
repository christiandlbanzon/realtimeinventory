from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
from zoneinfo import ZoneInfo

creds = Credentials.from_service_account_file('service-account-key.json', scopes=['https://www.googleapis.com/auth/spreadsheets'])
service = build('sheets', 'v4', credentials=creds)

tz = ZoneInfo('America/Puerto_Rico')
today = datetime.now(tz)
date_str = today.strftime('%Y-%m-%d')

result = service.spreadsheets().values().get(
    spreadsheetId='1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE',
    range='Montehiedra!A:ZZ'
).execute()

values = result.get('values', [])
headers = values[0] if values else []

# Find cherry cake columns
cherry_cols = []
for i, h in enumerate(headers):
    if h and ('cherry' in h.lower() or ('chocolate' in h.lower() and 'cake' in h.lower())):
        cherry_cols.append((i, h))

print('Cherry/Cake columns:', cherry_cols)

# Find today's date row
date_row_idx = None
for i, row in enumerate(values):
    if row and row[0] == date_str:
        date_row_idx = i
        break

if date_row_idx:
    print(f'\nDate row for {date_str} found at index {date_row_idx}')
    row_vals = values[date_row_idx]
    print('\nCherry Cake values:')
    for col_idx, col_name in cherry_cols:
        val = row_vals[col_idx] if col_idx < len(row_vals) else 'N/A'
        print(f'  {col_name}: {val}')
else:
    print(f'\nDate row for {date_str} NOT FOUND')
    print('Last few date rows:')
    for i in range(max(0, len(values) - 5), len(values)):
        if values[i] and values[i][0]:
            print(f'  Row {i}: {values[i][0]}')
