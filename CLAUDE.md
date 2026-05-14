# Drunken Cookies Real-Time Inventory — System Brief

You are joining an established system. Read this first, then `docs/RUNBOOK.md` for procedures and `docs/BUG_LEDGER.md` for known-but-out-of-scope issues. Today's tasks are usually:
- daily verification (Mall PARs sheet vs Clover API) for a given date
- ad-hoc fixes when the team flags something red
- menu rollovers (new cookie launches, retirements)
- forecast/sheet plumbing fixes

## What this system does

Cookie sales flow: **Clover POS (6 stores)** → **Cloud Run inventory-updater** (every 5 min) → **Google Sheets** (Mall PARs / Morning PARs / Dispatch PARs / Drunken Cookies historical). Morning PARs uses 4-week medians from the historical sheet to recommend daily bake quantities.

## The 6 stores

| Display name | Clover merchant ID | Notes |
|---|---|---|
| San Patricio | `Y3JSKHZKVKYM1` | mall, closed Sundays |
| Plaza del Sol | `J14BXNH1WDT71` | mall, closed Sundays |
| Montehiedra | `FNK14Z5E7CAA1` | mall, closed Sundays |
| Plaza Carolina | `S322BTDA07H71` | mall, closed Sundays |
| Plaza Las Americas | `3YCBMZQ6SFT71` | mall, mostly open Sundays |
| Old San Juan (VSJ) | `QJD3EASTRDBX1` | 24-hour, very high volume, "tail block" cols BT-CC on Mall PARs |

Order of stores in Mall PARs columns: SP (A-N) → PdS (P-AB) → MNT (AD-AP) → PCa (AR-BD) → PLA (BF-BR) → VSJ tail (BT-CC).

## Sheet IDs (memorise these)

| Sheet | ID | Notes |
|---|---|---|
| Mall PARs (April 2026) | `1C5_N8oHds9Xw9pqN5PptGAVHJ2WeKrh35PCiejusl88` | one sheet per month |
| **Mall PARs (May 2026)** | `1e5ri5yaXQMh6s4UhHTPNpLAGIWUgowCNnZDGzOgnerI` | active |
| **Morning PARs (May 2026)** | `1g9GCvm3xRziQCG03LIL9djk9drAdABXCYPioAtuU0zE` | one sheet per month; tabs `5-1`…`5-31` |
| **Dispatch PARs (May 2026)** | `171z2uZD-RtSnPFbs8H0elD74NZY4zeJlqJqZ7uBH8D0` | active |
| April Dispatch PARs (legacy) | `1XC9o3iGhv2YWAXZqnDwz0bxA1N4kJKkn_fswiz7X6ek` | watch for stale IMPORTRANGE pointing here |
| Drunken Cookies (historical) | `1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE` | tabs = store names; dates as rows; forecasts pull from `VSJ` tab |
| Sale Report 2026 | `1pGU5r-JQmJw2LbKHQqil84zTyAtacdxxDH50dTixNWQ` | weekly rollup tabs (e.g. `May 2 - May 8`) |

**Service-account email** (shared on every sheet we touch):
`703996360436-compute@developer.gserviceaccount.com`

## Cloud Run jobs (us-east1)

| Job | Purpose | Schedule |
|---|---|---|
| `inventory-updater` | every-5-min sync, writes today's totals | `*/5 * * * *` UTC |
| `inventory-updater-backfill` | re-process a specific date | `0 6 * * *` UTC = 2 AM PR (handles yesterday). Manual: `--update-env-vars=FOR_DATE=YYYY-MM-DD` |
| `daily-accuracy-report` | accuracy email (placeholder creds) | `0 7 * * *` UTC |
| `shopify-twice-daily` | unrelated | — |

Project: `boxwood-chassis-332307` · Image: `gcr.io/boxwood-chassis-332307/inventory-updater:latest` · Region: `us-east1`.

Rebuild + redeploy after any updater change:
```bash
gcloud builds submit --tag gcr.io/boxwood-chassis-332307/inventory-updater:latest --timeout=900 .
gcloud run jobs update inventory-updater          --region=us-east1 --image=gcr.io/boxwood-chassis-332307/inventory-updater:latest
gcloud run jobs update inventory-updater-backfill --region=us-east1 --image=gcr.io/boxwood-chassis-332307/inventory-updater:latest
```

## Menu rollout cadence (MEMORISE)

When a cookie launches on Mall PARs date **D**:
- **Morning PARs** roster updates on **D − 2** (bake starts 2 days early)
- **Dispatch PARs** roster updates on **D − 1** (ship day before)
- **Mall PARs** roster updates on **D** (sale day)

Same offset for retirements (Morning stops 2 days early so stock depletes). Apply to all three sheets when the team gives you a launch/retire date.

## Active menu (current as of last edit)

Letters A through P. J = Turron launches 5-15. K = `[NOT IN USE]` from 5-15 (was Vanilla Coconut Cream through 5-14). M = Birthday Cake "out of menu until sold out" — keep on sheet, hide on POS once depleted.

## Operating environment quirks

1. **Avast HTTPS scanning** on the user's Windows machine intercepts TLS to googleapis.com and Clover. If `requests`/`httplib2` throws `CERTIFICATE_VERIFY_FAILED`, run this once to append Avast's root to certifi:
   ```python
   import ssl, certifi, shutil
   src = r'C:/ProgramData/AVAST Software/Avast/wscert.der'
   pem = ssl.DER_cert_to_PEM_cert(open(src, 'rb').read())
   bundle = certifi.where()
   shutil.copy(bundle, bundle + '.bak')
   with open(bundle, 'a') as f:
       f.write('\n# Avast Web Shield Root\n' + pem)
   ```
   Then in every script that uses Google APIs / Clover:
   ```python
   import os, certifi
   os.environ['SSL_CERT_FILE'] = certifi.where()
   os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
   ```
2. **Sheets API quota**: 60 reads/min per user. Bursting causes 429s. Add `time.sleep(60)` between heavy iterations or stagger batchUpdate calls.
3. **Cloud Run jobs return success on partial failure** — they swallow 429 verification errors. If a write looks wrong, re-trigger the backfill instead of trusting the "Container exit(0)" message.
4. The terminal in this env is **bash** but the user's OS is **Windows**. Paths use `E:/prog fold/Drunken cookies/real-time-inventory/...` with forward slashes.

## What's been recently fixed (this codebase has scar tissue)

See `docs/BUG_LEDGER.md` for details. Headline:
- **Inventory-updater pagination** (`hasMore` field doesn't exist in Clover) — fixed via `len(page) >= limit`
- **Fuzzy cross-letter matching** routed old-menu items to current rows — fixed by enforcing same-letter constraint in `find_cookie_row`
- **`clean_cookie_name` obsolete substring remapping** cleared correct rows every run — fixed with canonical-format fast-path
- **Validation step compared full string** (`Black and White` vs `Black & White`) — fixed by letter-only comparison + `&`/`and` normalisation
- **Morning PARs H formula** (Sales Trend) didn't match `&` ↔ `and` in Drunken Cookies historical headers — fixed by adding REGEXREPLACE strip of `&` and `and` before non-alphanumeric strip
- **Sale Report 2026 weekly tabs** had stale IMPORTRANGE pointing to April Dispatch PARs — fix is to swap the URL when a new fully-May/June/etc. week is added

## Key Python files

| File | Purpose |
|---|---|
| `vm_inventory_updater_fixed.py` | the deployed updater — writes Mall PARs + Drunken Cookies |
| `sync_roster_week_job.py` | weekly roster sync (Friday 3 AM PR) from Clover → sheet column A labels |
| `error_alert_system.py` | daily accuracy email comparing sheet vs API, shared library for compare scripts |
| `compare_5_X.py` | one-off side-by-side sheet vs API for one date (use this template for new dates) |
| `Dockerfile`, `.gcloudignore` | build config — whitelist new .py files in `.gcloudignore` when adding them |

## How to start working on this codebase

1. Read this file (you just did)
2. Read `docs/RUNBOOK.md` for the playbooks (verify a day, backfill, menu rollover, etc.)
3. Read `docs/BUG_LEDGER.md` if you're touching the updater
4. Set up SSL fix if on the user's Windows machine
5. Ask the user what date / sheet they want checked

## Conventions

- Don't create new markdown files unless the user asks (this `docs/` directory and `.claude/skills/` exist because the user explicitly requested onboarding docs).
- The team manually fills column A on Mall PARs ("the roster"). The updater never touches column A — only sales-data columns. The `sync_roster_week_job.py` job sets roster labels on Fridays.
- Never write a literal value over a formula in column F, G, BV, or BW of Mall PARs unless asked — those are computed cells.
- Use letter slots (A, B, C, …) as the canonical identity; cookie names change with menu rotations.
