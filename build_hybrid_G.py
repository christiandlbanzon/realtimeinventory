"""Build Darren's phased forecast for Morning PARs column G (Malls + Website Forecast).
Same phases as H, preserving G's existing weekly day-offsets (6/13/20/27) and day-of-week standard.
TEST: writes only 5-26, reports values.
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

# Grab a clean original G formula from a tab that still has MEDIAN (5-27)
cur = svc.values().get(spreadsheetId=MORN, range="'5-27'!G5",
                       valueRenderOption='FORMULA').execute().get('values',[])[0][0]

# Prefix = everything up to (not including) "calc_result,"
split = cur.index("calc_result,")
prefix = cur[:split]

NEW_TAIL = (
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

new_g_row5 = prefix + NEW_TAIL
assert new_g_row5.count('(') == new_g_row5.count(')'), \
    f"Paren mismatch G: {new_g_row5.count('(')} vs {new_g_row5.count(')')}"
print("G paren balance OK")

# Write to 5-26 G3:G18
data = []
for row in range(3, 19):
    f = re.sub(r'\bA5\b', f'A{row}', new_g_row5)
    data.append({'range': f"'5-26'!G{row}", 'values': [[f]]})
svc.values().batchUpdate(spreadsheetId=MORN,
                         body={'valueInputOption':'USER_ENTERED','data':data}).execute()
print("Wrote G3:G18 on 5-26")
time.sleep(8)

after = svc.values().get(spreadsheetId=MORN, range="'5-26'!A3:H18",
                         valueRenderOption='UNFORMATTED_VALUE').execute().get('values',[])
print(f"\n{'Cookie':<28} {'G':>8} {'H':>8}")
print('-'*46)
for row in after:
    while len(row)<8: row.append('')
    print(f"{str(row[0])[:27]:<28} {str(row[6]):>8} {str(row[7]):>8}")
