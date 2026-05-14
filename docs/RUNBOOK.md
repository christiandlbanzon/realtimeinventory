# Runbook

Playbooks for the recurring tasks the user asks for. Read `CLAUDE.md` first.

---

## 1. Daily verification: Mall PARs sheet vs Clover API for date `Y-M-D`

User asks: "check data for 5-12" / "is X-Y running properly?"

```bash
cp compare_5_10.py compare_5_X.py
sed -i "s/2026, 5, 10/2026, 5, X/g; s/5-10/5-X/g" compare_5_X.py
python compare_5_X.py
```

Output: a per-store, per-letter table of `Sheet / API / Diff`. Sum the positives — that's how many cookies are missing from the sheet. The new updater code should produce zero diffs on any complete day.

What to flag:
- Per-store diff ≥ 20 → real sync issue, investigate
- Per-letter diff ≥ 5 at multiple stores → letter-mapping or roster issue
- VSJ very high diff on a recent day → late-night sales not yet backfilled (normal until 2 AM PR backfill runs)
- All zeros at 3 mall stores → check if it's Sunday (Plaza del Sol / Montehiedra / Plaza Carolina close Sundays)

Sundays only Plaza Las Americas, San Patricio, and VSJ are open. The 3 closed stores will read `0/0/0` legitimately.

---

## 2. Manual backfill of a date

User asks: "backfill 5-X" / "the 2 AM didn't run yet"

```bash
gcloud run jobs execute inventory-updater-backfill \
  --region=us-east1 \
  --update-env-vars=FOR_DATE=2026-05-X \
  --wait
```

`--wait` blocks ~30s. Drop `--wait` for fire-and-forget (use this for batches; see §3).

After it returns, **wait 70s for Sheets rate limit to clear** before re-running compare_5_X.py.

---

## 3. Backfill a date range (rebuilds historical data for forecasts)

User asks: "backfill last month so the forecast works properly"

Pattern: fire jobs async (don't wait), then wait ~4 minutes for completion, then verify Drunken Cookies sheet has values for new cookies in the relevant columns. See `backfill_30_days.sh` for the template.

```bash
for d in 2026-04-11 2026-04-12 ... 2026-05-10; do
  gcloud run jobs execute inventory-updater-backfill \
    --region=us-east1 --update-env-vars=FOR_DATE=$d --async
  sleep 2
done
```

---

## 4. Menu rollout (new cookie launch / retirement)

User shows a new menu image with launch date `D` and gives slot letter `X`.

Apply the **D-2 / D-1 / D cadence**:

```python
SHEETS = {
    'Mall PARs':     '1e5ri5yaXQMh6s4UhHTPNpLAGIWUgowCNnZDGzOgnerI',  # roster on D
    'Morning PARs':  '1g9GCvm3xRziQCG03LIL9djk9drAdABXCYPioAtuU0zE',  # roster on D-2
    'Dispatch PARs': '171z2uZD-RtSnPFbs8H0elD74NZY4zeJlqJqZ7uBH8D0',  # roster on D-1
}
# A12 = J row · A13 = K row · A11 = I row · etc. (row N = 3 + letter_index, letters A=3, B=4, ..., P=18)
```

Set column A on the affected tabs through end-of-month. Remind user that the team must:
1. Add `*X* Cookie Name` to Clover POS at all 6 stores
2. Hide / mark `hidden=true` on Clover for any retiring cookies before their D−2 date

---

## 5. Roster mismatch repair (sheet says NOT IN USE but POS still selling)

Symptoms: comparison shows large gaps on a specific letter at all stores; the sheet roster for that letter is `[NOT IN USE]`.

Two paths:
- **A (revert sheet)** — set roster A12/A13/etc. back to the still-selling cookie name through the cutover date; team finishes selling existing stock; then re-cut over.
- **B (hide on POS)** — keep the sheet roster as `[NOT IN USE]`; hide the Clover item so customers can't ring it up; team moves leftover stock off-POS.

Recommend A unless the user wants a hard cut.

---

## 6. Fixing the IMPORTRANGE month-rollover on Sale Report 2026

Symptom: weekly tab (e.g. `May 9 - May 15`) Website column T is all 0, %Website column U is `#DIV/0!`.

Cause: the bottom Mon-Thu IMPORTRANGE formulas (rows 28-43) point to the previous month's Dispatch PARs sheet ID.

Fix: replace OLD_ID with NEW_ID across the 64 formula cells (rows 28-43, columns B-E):
```python
OLD_ID = '1XC9o3iGhv2YWAXZqnDwz0bxA1N4kJKkn_fswiz7X6ek'  # April Dispatch
NEW_ID = '171z2uZD-RtSnPFbs8H0elD74NZY4zeJlqJqZ7uBH8D0'  # May Dispatch
# string replace OLD_ID -> NEW_ID in B28:E43 formulas, batch update
```

See `fix_may_2_8_website.py` for the working template.

---

## 7. Drunken Cookies sheet forecast not matching for a new cookie

Symptom: a new cookie's Sales Trend column on Morning PARs shows `48` (the standard_val fallback) instead of a real median.

Possible causes (in order of likelihood):
1. **Historical data missing**: cookie launched < 4 weeks ago. Acceptable; will self-resolve. Or run a 30-day backfill.
2. **Header mismatch**: Drunken Cookies col header uses `&` but sheet roster uses `and`. The H formula now normalises both (`docs/BUG_LEDGER.md` entry 4); if the issue resurfaces, regex broke.
3. **Letter prefix mismatch**: forecast strips `^[A-Z]\s*-\s*` from both sides, so flavor matching is letter-agnostic. If a Drunken Cookies col is `"O - Foo"` and roster is `"O - Bar"`, that's a real mismatch — fix the column header or roster.

To diagnose, read formula at `'5-X'!H<row>` valueRenderOption=FORMULA and trace the LET variables manually.

---

## 8. Adding a new compare script or helper

When creating a Python helper that hits Google/Clover, include the Avast SSL fix at the top:
```python
import os, certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
```

If the script will be deployed (e.g. to Cloud Run), add it to `.gcloudignore` whitelist (with `!filename.py`) and `Dockerfile` COPY.
