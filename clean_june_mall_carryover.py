"""Clean May carryover from June Mall PARs — position-aware (sections detected per tab).

Clears ONLY manual-entry data that shouldn't exist on a future date:
  1. Top-grid Ending Inventory columns (manual count) rows 3-18: I, W, AK, AY, BM, BW
     (clear literals + pure-arithmetic hardcodes like =4+12; never touch real formulas)
  2. CLOSING INVENTORY section: per-cookie rows (between the 'CLOSING INVENTORY' header and
     its 'TOTAL'), cols B-E literals. Preserves col A labels and the TOTAL row.
  3. Cookie Shots section: the 2 data rows after the 'Cookie Shots' header, cols B-F literals
     (includes the '(2) 5/2' expiration notes).

Preserves: all headers, all real (cell-referencing) formulas, TOTAL rows, column A labels.

DRY_RUN toggles between report-only and actual clear.
"""
import os, certifi, re, time
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

DRY_RUN = True  # set False to actually clear
JUNE_MALL = '1DA2R17K01L1I8vFM61ttkcRt2_1qcLxYwlcu_9Qcs4I'
creds = Credentials.from_service_account_file('service-account-key.json',
                                                scopes=['https://www.googleapis.com/auth/spreadsheets'])
svc = build('sheets', 'v4', credentials=creds).spreadsheets()

m = svc.get(spreadsheetId=JUNE_MALL, fields='sheets.properties.title').execute()
tabs = sorted([s['properties']['title'] for s in m['sheets'] if s['properties']['title'].startswith('6-')],
              key=lambda t: int(t.split('-')[1]))

ENDINV_COLS = {8:'I', 22:'W', 36:'AK', 50:'AY', 64:'BM', 74:'BW'}  # idx -> letter

def colL(idx):
    s = ''
    idx += 1
    while idx:
        idx, r = divmod(idx-1, 26)
        s = chr(65+r) + s
    return s

def is_arith_hardcode(v):
    # formula like =4+12, =48+8 (digits, +, -, spaces only)
    if not str(v).startswith('='):
        return False
    body = str(v)[1:]
    return bool(re.fullmatch(r'[\d+\-*/.\s]+', body))

def is_literal(v):
    if v == '' or v is None:
        return False
    if str(v).startswith('='):
        return False
    return True

total_cells = 0
tab_reports = {}

for tab in tabs:
    grid = svc.values().get(spreadsheetId=JUNE_MALL, range=f"'{tab}'!A1:CC50",
                            valueRenderOption='FORMULA').execute().get('values',[])
    def cell(r, c):
        return grid[r][c] if (r < len(grid) and c < len(grid[r])) else ''

    colA = [ (cell(r,0) if cell(r,0) else '') for r in range(len(grid)) ]
    def find_row(substr, start=0):
        for r in range(start, len(colA)):
            if substr.upper() in str(colA[r]).upper():
                return r
        return None

    clears = []

    # --- 1. Ending Inventory columns rows 3-18 (idx 2-17) ---
    for cidx in ENDINV_COLS:
        for r in range(2, 18):
            v = cell(r, cidx)
            if is_literal(v) or is_arith_hardcode(v):
                # exclude 0 literals (harmless) but clear arithmetic & nonzero
                if is_arith_hardcode(v) or (is_literal(v) and str(v).strip() not in ('0','')):
                    clears.append(f"{colL(cidx)}{r+1}")

    # --- 2. CLOSING INVENTORY section ---
    ci_hdr = find_row('CLOSING INVENTORY')
    if ci_hdr is not None:
        ci_total = find_row('TOTAL', start=ci_hdr+1)
        end = ci_total if ci_total else ci_hdr+18
        for r in range(ci_hdr+1, end):   # data rows, excludes TOTAL
            for c in range(1, 5):  # B-E
                v = cell(r, c)
                if is_literal(v) and str(v).strip() not in ('0',''):
                    clears.append(f"{colL(c)}{r+1}")

    # --- 3. Cookie Shots section ---
    cs_hdr = find_row('Cookie Shots')
    if cs_hdr is not None:
        # data rows = the next rows until a blank col-A or the CLOSING INVENTORY header
        ci_for_stop = ci_hdr if ci_hdr else cs_hdr+5
        for r in range(cs_hdr+1, min(cs_hdr+4, ci_for_stop)):
            label = str(cell(r,0)).strip()
            if not label:
                continue
            for c in range(1, 6):  # B-F (incl notes)
                v = cell(r, c)
                if is_literal(v) and str(v).strip() not in ('0',''):
                    clears.append(f"{colL(c)}{r+1}")

    clears = sorted(set(clears))
    if clears:
        tab_reports[tab] = clears
        total_cells += len(clears)

# Report
for tab, clears in tab_reports.items():
    print(f"{tab}: {len(clears)} cells -> {clears}")
print(f"\nTOTAL: {total_cells} cells across {len(tab_reports)} tabs")
print(f"DRY_RUN = {DRY_RUN}")

if not DRY_RUN and tab_reports:
    # Build batchClear requests
    ranges = []
    for tab, clears in tab_reports.items():
        for c in clears:
            ranges.append(f"'{tab}'!{c}")
    # batchClear in chunks
    CH = 100
    cleared = 0
    for k in range(0, len(ranges), CH):
        svc.values().batchClear(spreadsheetId=JUNE_MALL, body={'ranges': ranges[k:k+CH]}).execute()
        cleared += len(ranges[k:k+CH])
        time.sleep(1)
    print(f"\nCLEARED {cleared} cells.")
