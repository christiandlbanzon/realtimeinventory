"""Build Darren's phased forecast for Morning PARs column H (VSJ Sales Trend).

Phases (by cookie maturity, preserving the existing 2-day-window unit):
  - mature  (4 weekly same-weekday windows present, nv==4) -> MEDIAN(w1..w4)   [unchanged behavior]
  - young   (>=4 recent daily windows, dv>=4, but <4 weeks)  -> AVERAGE(d1..d4)
  - ramp    (1-3 recent daily windows, dv 1..3)              -> MAX(d1, standard)  [prev day if it beats standard]
  - launch  (no data, dv==0)                                 -> standard

win(off) = 2-day window = INDEX(date-off) + INDEX(date-off+1), same convention as the original get_sales.
TEST MODE: writes only to the 5-26 tab and reports before/after. Does NOT propagate.
"""
import os, certifi, time
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

MORN = '1g9GCvm3xRziQCG03LIL9djk9drAdABXCYPioAtuU0zE'
creds = Credentials.from_service_account_file('service-account-key.json',
                                                scopes=['https://www.googleapis.com/auth/spreadsheets'])
svc = build('sheets', 'v4', credentials=creds).spreadsheets()

# 1. Grab current H5 to reuse the exact prefix (IMPORTRANGE + clean regex lines w/ special chars)
cur = svc.values().get(spreadsheetId=MORN, range="'5-26'!H5",
                       valueRenderOption='FORMULA').execute().get('values',[])[0][0]

MARKER = "IF(ISERROR(col_num), standard_val,"
idx = cur.index(MARKER)
prefix = cur[:idx]

# Walk from idx to find where the IF(ISERROR ...) expression closes (depth back to 0)
depth = 0
end = None
for i in range(idx, len(cur)):
    c = cur[i]
    if c == '(':
        depth += 1
    elif c == ')':
        depth -= 1
        if depth == 0:
            end = i
            break
outer_closers = cur[end+1:]  # trailing ) that close data-LET / IF(raw_target) / outer LET

NEW_BLOCK = (
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

new_formula_row5 = prefix + NEW_BLOCK + outer_closers

# Quick paren balance check
assert new_formula_row5.count('(') == new_formula_row5.count(')'), \
    f"Paren mismatch: {new_formula_row5.count('(')} vs {new_formula_row5.count(')')}"
print("Paren balance OK")

# Capture BEFORE values
before = svc.values().get(spreadsheetId=MORN, range="'5-26'!A3:H18",
                          valueRenderOption='UNFORMATTED_VALUE').execute().get('values',[])

# Write new formula to H3:H18 (substitute A5 -> A{row})
import re
data = []
for row in range(3, 19):
    f = re.sub(r'\bA5\b', f'A{row}', new_formula_row5)
    data.append({'range': f"'5-26'!H{row}", 'values': [[f]]})
svc.values().batchUpdate(spreadsheetId=MORN,
                         body={'valueInputOption':'USER_ENTERED','data':data}).execute()
print("Wrote H3:H18 on 5-26")
time.sleep(8)

after = svc.values().get(spreadsheetId=MORN, range="'5-26'!A3:H18",
                         valueRenderOption='UNFORMATTED_VALUE').execute().get('values',[])

print(f"\n{'Cookie':<28} {'H before':>9} {'H after':>9}")
print('-'*50)
for i in range(len(after)):
    nm = str(after[i][0])[:27] if after[i] else ''
    hb = before[i][7] if len(before[i])>7 else ''
    ha = after[i][7] if len(after[i])>7 else ''
    print(f"{nm:<28} {str(hb):>9} {str(ha):>9}")
