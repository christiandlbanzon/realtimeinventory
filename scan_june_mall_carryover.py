"""Scan June Mall PARs for stale carryover data (hardcoded literals where formulas/blanks expected).
Checks: column I (Ending Inv) hardcoded numbers, bottom CLOSING INVENTORY rows 27-43,
Cookie Shots rows 21-23. Reports per tab."""
import os, certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

JUNE_MALL = '1DA2R17K01L1I8vFM61ttkcRt2_1qcLxYwlcu_9Qcs4I'
creds = Credentials.from_service_account_file('service-account-key.json',
                                                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
svc = build('sheets', 'v4', credentials=creds).spreadsheets()

m = svc.get(spreadsheetId=JUNE_MALL, fields='sheets.properties.title').execute()
tabs = sorted([s['properties']['title'] for s in m['sheets'] if s['properties']['title'].startswith('6-')],
              key=lambda t: int(t.split('-')[1]))

# For each tab, read formulas+values for the full grid we care about (A1:CC43)
print(f"Scanning {len(tabs)} June Mall PARs tabs for carryover...\n")
summary = {}
for tab in tabs:
    vals = svc.values().get(spreadsheetId=JUNE_MALL, range=f"'{tab}'!A1:CC43",
                            valueRenderOption='FORMULA').execute().get('values',[])
    # normalize to grid
    def cell(r, c):  # r,c 0-indexed
        if r < len(vals) and c < len(vals[r]):
            return vals[r][c]
        return ''
    issues = []
    # Bottom CLOSING INVENTORY section rows 27-43 (idx 26-42), cols B-E (idx 1-4) — should be blank on future dates
    for r in range(26, 43):
        for c in range(1, 6):
            v = cell(r, c)
            if v != '' and not str(v).startswith('='):
                # it's a hardcoded literal
                try:
                    num = float(v)
                    if num != 0:
                        colL = chr(65+c)
                        issues.append(f"{colL}{r+1}={v}")
                except (ValueError, TypeError):
                    pass
    # Cookie shots rows 21-23 (idx 20-22) cols B-F
    for r in range(20, 23):
        for c in range(1, 6):
            v = cell(r, c)
            if v != '' and not str(v).startswith('='):
                try:
                    if float(v) != 0:
                        issues.append(f"{chr(65+c)}{r+1}={v}")
                except (ValueError, TypeError):
                    if str(v).strip():  # non-empty text like "(2) 5/2"
                        issues.append(f"{chr(65+c)}{r+1}='{v}'")
    # Top grid: Ending Inventory columns per store (I=8, W=22, AK=36, AY=50, BM=64, and VSJ BW=74) rows 3-18 — should be blank/formula
    # Actually col I (idx 8) = SP Ending Inv. Check hardcoded literals (red cells like =4+12 or plain nums)
    endinv_cols = {8:'I(SP)', 22:'W(PdS)', 36:'AK(Mnt)', 50:'AY(PCa)', 64:'BM(PLA)', 74:'BW(VSJ)'}
    for c, label in endinv_cols.items():
        for r in range(2, 18):
            v = cell(r, c)
            if v != '' and not str(v).startswith('='):
                try:
                    if float(v) != 0:
                        issues.append(f"{label}@row{r+1}={v}")
                except (ValueError, TypeError):
                    pass
            elif str(v).startswith('=') and ('+' in str(v) and all(ch.isdigit() or ch in '=+ ' for ch in str(v))):
                # hardcoded arithmetic like =4+12
                issues.append(f"{label}@row{r+1}={v} (HARDCODED ARITH)")
    if issues:
        summary[tab] = issues

if not summary:
    print("No carryover found.")
else:
    for tab, issues in summary.items():
        print(f"{tab}: {len(issues)} stray cells")
        print(f"   {issues}")
    print(f"\nTOTAL tabs affected: {len(summary)} / {len(tabs)}")
