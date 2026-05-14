---
name: verify-day
description: Compare Mall PARs sheet vs Clover API for a target date across all 6 stores. Use when user asks "check data for 5-X", "is X working properly", "side-by-side for date Y", or anything implying daily sheet-vs-API reconciliation.
---

# Verify a day's Mall PARs data

1. Make a copy of the most recent `compare_5_X.py` template:
   ```bash
   cd "E:/prog fold/Drunken cookies/real-time-inventory"
   cp compare_5_10.py compare_5_<DAY>.py
   sed -i "s/2026, 5, 10/2026, 5, <DAY>/g; s/5-10/5-<DAY>/g" compare_5_<DAY>.py
   python compare_5_<DAY>.py
   ```

2. Read the output table (per-store × per-letter `Sheet/API/Diff`) and present to the user:
   - All zeros → ✅ 100% match
   - Per-store sum < 5 → likely timing (recent sales not synced yet)
   - Per-store sum ≥ 20 → real sync problem; trigger a manual backfill (see `docs/RUNBOOK.md` §2)
   - 3 mall stores all zero on a Sunday → expected (Plaza del Sol, Montehiedra, Plaza Carolina close Sundays)

3. If gaps exist and the day is complete, try a manual backfill:
   ```bash
   gcloud run jobs execute inventory-updater-backfill --region=us-east1 \
     --update-env-vars=FOR_DATE=2026-05-<DAY> --wait
   ```
   Then **wait 70 seconds** for Sheets rate limit and re-run the comparison.

4. Always include the Avast SSL workaround imports at the top of any Python that hits Google/Clover.

5. When reporting back, include: per-store totals, any cell-level outliers, and whether the result is the "final" state (post-backfill) or a snapshot (mid-day).
