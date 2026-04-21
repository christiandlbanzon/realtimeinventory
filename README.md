# Drunken Cookies — Real-Time Inventory System 🍪

Automated system that syncs Clover POS sales data into Google Sheets every 5 minutes. Powers the PAR (baking forecast) sheets used by the production team.

---

## Architecture

```
┌──────────────┐       ┌─────────────────┐       ┌──────────────────┐
│  Clover POS  │──────▶│ inventory-      │──────▶│  Google Sheets   │
│  (6 stores)  │       │ updater         │       │  (Mall PARs,     │
│              │       │ (every 5 min)   │       │   Dispatch PARs, │
└──────────────┘       └─────────────────┘       │   Morning PARs)  │
                                                  └──────────────────┘
                                                          │
                              ┌───────────────────────────┘
                              ▼
                       ┌──────────────┐
                       │   Drunken    │
                       │  Cookies DB  │◀── historical data used for
                       │   (Sheet)    │    4-week median PAR forecasts
                       └──────────────┘
```

---

## Deployed Cloud Run Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `inventory-updater` | Every 5 min | Pull Clover sales → write to Mall PARs + Drunken Cookies |
| `daily-sales-automation` | Daily 6 AM PR | End-of-day sales summary |
| `shopify-twice-daily` | 6 PM + midnight UTC | Shopify online orders → Dispatch PARs |
| `inventory-roster-sync` | **Manual only** | Update cookie roster when menu changes |

---

## Key Files

| File | What it does |
|------|--------------|
| `vm_inventory_updater_fixed.py` | Main inventory updater — Clover API → Sheets |
| `sync_cookie_roster_from_clover.py` | Updates cookie name labels (A–N) when menu changes |
| `sync_roster_week_job.py` | Weekly roster sync (writes tomorrow + next 7 days) |
| `sync_roster_job.py` | Single-day roster sync helper |
| `Dockerfile` | Inventory updater container |
| `Dockerfile.roster` | Roster sync container |

---

## Locations

| Store | Clover Merchant ID | Mall PARs column | Drunken Cookies tab |
|-------|--------------------|--------------------| --------------------|
| San Patricio | Y3JSKHZKVKYM1 | F | San Patricio |
| Plaza del Sol | J14BXNH1WDT71 | T | PlazaSol |
| Montehiedra | FNK14Z5E7CAA1 | AH | Montehiedra |
| Plaza Carolina | S322BTDA07H71 | AV | Plaza Carolina |
| Plaza Las Americas | 3YCBMZQ6SFT71 | BJ | Plaza |
| Old San Juan (VSJ) | QJD3EASTRDBX1 | BU | VSJ |

---

## Google Sheets

| Sheet | ID | What it shows |
|-------|-------|---------------|
| Mall PARs (April 2026) | `1C5_N8oHds9Xw9pqN5PptGAVHJ2WeKrh35PCiejusl88` | Live sales + inventory per store |
| Dispatch PARs | `1XC9o3iGhv2YWAXZqnDwz0bxA1N4kJKkn_fswiz7X6ek` | Tomorrow's bake forecast per store |
| Morning PARs | `1BbZc3DYa3r0aCR2jiwm6ecs7cs7v4IRO39nHFIYR1oc` | VSJ morning production list |
| Drunken Cookies (database) | `1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE` | Historical sales (source of truth) |

---

## How the PAR Formula Works

For each cookie at each store on a given day:

1. **Try 4-week median** — look at the same day + next day for 4 weeks back, sum each pair, take median
2. **If only 1 week of data** → use that week's value
3. **If 2+ weeks** → median of available weeks
4. **If brand new cookie (0 weeks)** →
   - Mon/Tue/Wed: use yesterday's actual sales
   - Thu/Fri/Sat/Sun: use standard table (15/15/10/5 for small stores, 30/30/30/20 for Plaza Las Americas, 48 for VSJ)

---

## Common Operations

### Run inventory-updater manually
```bash
gcloud run jobs execute inventory-updater --region=us-east1
```

### Run roster sync when menu changes
```bash
gcloud run jobs execute inventory-roster-sync --region=us-east1
```

### Rebuild and deploy inventory-updater
```bash
gcloud builds submit --tag gcr.io/boxwood-chassis-332307/inventory-updater
gcloud run jobs update inventory-updater --region=us-east1 --image=gcr.io/boxwood-chassis-332307/inventory-updater:latest
```

### Rebuild and deploy roster sync
```bash
gcloud builds submit --config=cloudbuild.roster.yaml
gcloud run jobs update inventory-roster-sync --region=us-east1 --image=gcr.io/boxwood-chassis-332307/inventory-roster-sync:latest
```

---

## Credentials (not in git)

- `clover_creds.json` — Clover API tokens per store
- `service-account-key.json` — Google service account for Sheets access

These are loaded into the Docker images at build time and stored as GCP secrets.

---

## Key Fixes Applied

- **Dubai Chocolate mapping** — removed hardcoded `Dubai Chocolate → Birthday Cake` rule
- **Expected Live Inventory formulas** — updater no longer overwrites these with hardcoded 0
- **NOT IN USE rows** — cleaned of stale template values on tabs 4-8 through 4-30
- **Sheets API retry** — 429 rate limit handling with exponential backoff
- **Morning PARs formula** — progressive median (1 week, 2 weeks, 3 weeks, 4 weeks) with proper fallback table
- **Dispatch PARs formula** — same progressive median logic + day-of-week fallback
- **Drunken Cookies database** — append-only column policy, never rename existing headers
