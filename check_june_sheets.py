"""Inspect June sheets: confirm tabs exist, formulas intact, no premature live data."""
import os, certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_service_account_file('service-account-key.json',
                                                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
svc = build('sheets', 'v4', credentials=creds).spreadsheets()

SHEETS = {
    'Mall PARs (June)':     '1DA2R17K01L1I8vFM61ttkcRt2_1qcLxYwlcu_9Qcs4I',
    'Morning PARs (June)':  '1HwlCIERM3gbnvVv8q26z4_wDKZvVg4NKGCEwCsplW_8',
    'Dispatch PARs (June)': '1StKuCgL0gXnioR6yBPKRQeA-VRxkZEhA14N28ZSyLGU',
}

def tab_list(sid):
    m = svc.get(spreadsheetId=sid, fields='sheets.properties.title').execute()
    return [s['properties']['title'] for s in m['sheets']]

for name, sid in SHEETS.items():
    print(f"\n{'='*65}\n{name}\n{'='*65}")
    tabs = tab_list(sid)
    june_tabs = sorted([t for t in tabs if t.startswith('6-')], key=lambda t: int(t.split('-')[1]) if t.split('-')[1].isdigit() else 99)
    other_tabs = [t for t in tabs if not t.startswith('6-')]
    print(f"  Total tabs: {len(tabs)}  (June day-tabs: {len(june_tabs)}, other: {len(other_tabs)})")
    if june_tabs:
        print(f"  June tabs: {june_tabs[0]} ... {june_tabs[-1]}")
    if other_tabs:
        print(f"  Other tabs: {other_tabs[:8]}")
    # Spot-check 6-1 and 6-15: roster col A, key formula cells, look for premature data
    for tab in ['6-1', '6-15', '6-30']:
        if tab not in tabs:
            print(f"  -- {tab}: NOT FOUND")
            continue
        # Roster col A (cookies)
        rA = svc.values().get(spreadsheetId=sid, range=f"'{tab}'!A3:A18").execute().get('values',[])
        roster = [r[0] if r else '' for r in rA]
        print(f"  {tab} roster A3:A18: {roster}")
        # Check for any live numeric data in the body (rows 3-18, cols B onwards). For Mall PARs, look at Live Sales cols (F/T/AH/AV/BJ/BU)
        if 'Mall' in name:
            live_cols = ['F', 'T', 'AH', 'AV', 'BJ', 'BU']
            label = 'Live Sales'
        elif 'Morning' in name:
            live_cols = ['D']  # Amount to bake — usually has values when team enters
            label = 'D (Amount)'
        else:  # Dispatch
            live_cols = ['B','C','D']  # spot check first few data cols
            label = 'B/C/D'
        any_data = []
        for c in live_cols:
            vals = svc.values().get(spreadsheetId=sid, range=f"'{tab}'!{c}3:{c}18",
                                    valueRenderOption='UNFORMATTED_VALUE').execute().get('values',[])
            for i, row in enumerate(vals):
                v = row[0] if row else ''
                if isinstance(v, (int, float)) and v != 0:
                    any_data.append(f"{c}{i+3}={v}")
        print(f"  {tab} {label} non-zero numeric cells: {len(any_data)} (first few: {any_data[:5]})")
        # Check a key formula cell to confirm not erased
        if 'Morning' in name:
            f_cell = svc.values().get(spreadsheetId=sid, range=f"'{tab}'!G5",
                                       valueRenderOption='FORMULA').execute().get('values',[])
            g_formula = f_cell[0][0] if f_cell and f_cell[0] else ''
            print(f"  {tab} G5 starts with: {g_formula[:80]!r}{'...' if len(g_formula)>80 else ''}")
            f_cell = svc.values().get(spreadsheetId=sid, range=f"'{tab}'!H5",
                                       valueRenderOption='FORMULA').execute().get('values',[])
            h_formula = f_cell[0][0] if f_cell and f_cell[0] else ''
            print(f"  {tab} H5 starts with: {h_formula[:80]!r}{'...' if len(h_formula)>80 else ''}")
            # Check if it's the hybrid
            full_h = h_formula
            print(f"  {tab} H5 hybrid present (has num_valid+day_valid)? {('num_valid' in full_h and 'day_valid' in full_h)}")
        elif 'Mall' in name:
            # Check chain formula on row 5 (col H = San Patricio closing inv)
            for c in ['H5', 'V5', 'BV5']:
                f_cell = svc.values().get(spreadsheetId=sid, range=f"'{tab}'!{c}",
                                           valueRenderOption='FORMULA').execute().get('values',[])
                f = f_cell[0][0] if f_cell and f_cell[0] else ''
                is_formula = f.startswith('=')
                print(f"  {tab} {c}: formula={is_formula} {('starts with: ' + f[:60]) if is_formula else 'value=' + f}")
        else:  # Dispatch
            # Sample a couple of cells
            for c in ['B5', 'F5', 'K5']:
                f_cell = svc.values().get(spreadsheetId=sid, range=f"'{tab}'!{c}",
                                           valueRenderOption='FORMULA').execute().get('values',[])
                f = f_cell[0][0] if f_cell and f_cell[0] else ''
                is_formula = f.startswith('=')
                print(f"  {tab} {c}: formula={is_formula}  {(f[:60] + '...') if is_formula else 'value=' + str(f)}")
