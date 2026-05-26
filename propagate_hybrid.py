"""Propagate the phased (Darren hybrid) G & H formulas to Morning PARs tabs 5-27..5-31.
5-26 already done. Builds both formulas from a current tab's prefix, swaps the statistic tail.
"""
import os, certifi, time, re
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

MORN = '1g9GCvm3xRziQCG03LIL9djk9drAdABXCYPioAtuU0zE'
creds = Credentials.from_service_account_file('service-account-key.json',
                                                scopes=['https://www.googleapis.com/auth/spreadsheets'])
svc = build('sheets', 'v4', credentials=creds).spreadsheets()

TARGET_TABS = ['5-27', '5-28', '5-29', '5-30', '5-31']

# ---- Build H row-5 formula (from a tab still on original; use 5-27 H5) ----
hcur = svc.values().get(spreadsheetId=MORN, range="'5-27'!H5", valueRenderOption='FORMULA').execute().get('values',[])[0][0]
MARK = "IF(ISERROR(col_num), standard_val,"
i = hcur.index(MARK)
hpre = hcur[:i]
depth = 0; end = None
for j in range(i, len(hcur)):
    if hcur[j] == '(': depth += 1
    elif hcur[j] == ')':
        depth -= 1
        if depth == 0: end = j; break
hclose = hcur[end+1:]
H_BLOCK = (
"IF(ISERROR(col_num), standard_val,\n"
"  LET(\n"
"    win, LAMBDA(off, LET(ds, TEXT(dateRef-off, \"yyyy-mm-dd\"), ri, MATCH(ds, dates_text, 0), "
"IF(ISERROR(ri), 0, IFERROR(INDEX(data, ri, col_num)*1 + INDEX(data, ri+1, col_num)*1, 0)))),\n"
"    wk_one, win(7), wk_two, win(14), wk_three, win(21), wk_four, win(28),\n"
"    num_valid, IF(wk_one>0,1,0)+IF(wk_two>0,1,0)+IF(wk_three>0,1,0)+IF(wk_four>0,1,0),\n"
"    day_one, win(1), day_two, win(2), day_three, win(3), day_four, win(4),\n"
"    day_valid, IF(day_one>0,1,0)+IF(day_two>0,1,0)+IF(day_three>0,1,0)+IF(day_four>0,1,0),\n"
"    IF(num_valid=4, MEDIAN(wk_one,wk_two,wk_three,wk_four), "
"IF(day_valid=0, standard_val, IF(day_valid<4, MAX(day_one, standard_val), AVERAGE(day_one,day_two,day_three,day_four))))\n"
"  )"
")"
)
H5 = hpre + H_BLOCK + hclose
assert H5.count('(') == H5.count(')'), "H paren mismatch"

# ---- Build G row-5 formula ----
gcur = svc.values().get(spreadsheetId=MORN, range="'5-27'!G5", valueRenderOption='FORMULA').execute().get('values',[])[0][0]
gsplit = gcur.index("calc_result,")
gpre = gcur[:gsplit]
G_TAIL = (
"nz, LAMBDA(x, IF(ISNUMBER(x), x, 0)),\n"
"    wk_one, nz(get_val(6)), wk_two, nz(get_val(13)), wk_three, nz(get_val(20)), wk_four, nz(get_val(27)),\n"
"    num_valid, IF(wk_one>0,1,0)+IF(wk_two>0,1,0)+IF(wk_three>0,1,0)+IF(wk_four>0,1,0),\n"
"    day_one, nz(get_val(1)), day_two, nz(get_val(2)), day_three, nz(get_val(3)), day_four, nz(get_val(4)),\n"
"    day_valid, IF(day_one>0,1,0)+IF(day_two>0,1,0)+IF(day_three>0,1,0)+IF(day_four>0,1,0),\n"
"    standard, IFS($C$1=\"Thursday\",48,$C$1=\"Friday\",48,$C$1=\"Saturday\",38,$C$1=\"Sunday\",38,$C$1=\"Monday\",38,$C$1=\"Tuesday\",38,$C$1=\"Wednesday\",38),\n"
"    IF(num_valid=4, MEDIAN(wk_one,wk_two,wk_three,wk_four), "
"IF(day_valid=0, standard, IF(day_valid<4, MAX(day_one, standard), AVERAGE(day_one,day_two,day_three,day_four))))\n"
"  )\n"
")"
)
G5 = gpre + G_TAIL
assert G5.count('(') == G5.count(')'), "G paren mismatch"
print("Both formulas balanced. Propagating to", TARGET_TABS)

# ---- Write to all target tabs, rows 3-18 ----
data = []
for tab in TARGET_TABS:
    for row in range(3, 19):
        data.append({'range': f"'{tab}'!G{row}", 'values': [[re.sub(r'\bA5\b', f'A{row}', G5)]]})
        data.append({'range': f"'{tab}'!H{row}", 'values': [[re.sub(r'\bA5\b', f'A{row}', H5)]]})

# batch in chunks to avoid payload limits
CH = 60
total = 0
for k in range(0, len(data), CH):
    resp = svc.values().batchUpdate(spreadsheetId=MORN,
        body={'valueInputOption':'USER_ENTERED','data':data[k:k+CH]}).execute()
    total += resp.get('totalUpdatedCells', 0)
    time.sleep(2)
print(f"Updated {total} cells across {len(TARGET_TABS)} tabs (G & H, rows 3-18)")
