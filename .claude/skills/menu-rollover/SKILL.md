---
name: menu-rollover
description: Apply a menu change (new cookie launch, retirement, slot reassignment) with the correct production lead-time cadence across Mall/Morning/Dispatch PARs. Use when user shows a menu image with a launch date or says "new menu adjust accordingly", "starts on 5-15", etc.
---

# Menu rollover

## The cadence rule (memorise)

For a cookie that goes live on Mall PARs on date **D**:
- **Morning PARs** roster updates on **D − 2** (bake starts 2 days early)
- **Dispatch PARs** roster updates on **D − 1** (ship day before)
- **Mall PARs** roster updates on **D** (sale day)

Same offset reversed for retirements (Morning stops 2 days early so existing stock depletes).

## Cookie → row mapping

Cookie data on PARs sheets starts at **row 3** (`A - …`), one row per letter A through P. So:

| Letter | Row | Letter | Row |
|---|---|---|---|
| A | 3 | I | 11 |
| B | 4 | J | 12 |
| C | 5 | K | 13 |
| D | 6 | L | 14 |
| E | 7 | M | 15 |
| F | 8 | N | 16 |
| G | 9 | O | 17 |
| H | 10 | P | 18 |

Total row is 19. Don't touch it.

## Sheet IDs

```python
SHEETS = {
    'Mall PARs':     '1e5ri5yaXQMh6s4UhHTPNpLAGIWUgowCNnZDGzOgnerI',  # May 2026
    'Morning PARs':  '1g9GCvm3xRziQCG03LIL9djk9drAdABXCYPioAtuU0zE',
    'Dispatch PARs': '171z2uZD-RtSnPFbs8H0elD74NZY4zeJlqJqZ7uBH8D0',
}
```

When a new month rolls over, find the new Mall PARs ID by looking at recent commits or asking the user. Update `MALL_PARS_BY_MONTH` in `error_alert_system.py`.

## Application pattern (Python)

```python
import os, certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_service_account_file('service-account-key.json',
                                                scopes=['https://www.googleapis.com/auth/spreadsheets'])
svc = build('sheets', 'v4', credentials=creds).spreadsheets()

# Example: J launches on 5-15, set roster J-Turron through 5-31
LAUNCH_DAY = 15
NEW_LABEL = 'J - Turron'
LETTER_ROW = 12  # J

def apply(sheet_id, start_day, end_day=31):
    tabs = [f'5-{d}' for d in range(start_day, end_day+1)]
    data = [{'range': f"'{t}'!A{LETTER_ROW}", 'values': [[NEW_LABEL]]} for t in tabs]
    return svc.values().batchUpdate(spreadsheetId=sheet_id,
        body={'valueInputOption':'USER_ENTERED','data':data}).execute()

apply('1g9GCvm3xRziQCG03LIL9djk9drAdABXCYPioAtuU0zE', LAUNCH_DAY - 2)  # Morning: D-2
apply('171z2uZD-RtSnPFbs8H0elD74NZY4zeJlqJqZ7uBH8D0', LAUNCH_DAY - 1)  # Dispatch: D-1
apply('1e5ri5yaXQMh6s4UhHTPNpLAGIWUgowCNnZDGzOgnerI', LAUNCH_DAY)      # Mall: D
```

## After updating sheet rosters

Tell the user the team must, before Mall PARs date D:
1. **Add to Clover POS** the new item `*X* Cookie Name` at all 6 stores
2. **Hide on Clover POS** any retiring cookie's items (mark `hidden=true` or `available=false`)

If they don't do (1), the new cookie's row will read 0 on D (POS has nothing to ring up under that letter).
If they don't do (2), the retired cookie's sales still hit Clover but have no slot on the sheet → invisible cookies and inventory math gets off.

## Special-case: "out of menu until sold out"

This means: keep the cookie on the sheet roster, keep selling existing stock, hide on POS only when stock hits zero. Don't change the sheet roster — change happens organically when team confirms depletion.

## Special-case: `[NOT IN USE]` slot

If a letter slot is being deactivated and nothing replaces it, set roster to `[NOT IN USE]` (with brackets, exact case). The Morning PARs F/G/H formulas have explicit guards `IF(A = "[NOT IN USE]", 0, ...)` that fire correctly only with this exact string.
