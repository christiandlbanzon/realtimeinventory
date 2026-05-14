# Bug Ledger

Hard-won lessons. Read before touching `vm_inventory_updater_fixed.py` or any LET/IMPORTRANGE formula.

---

## Fixed (don't reintroduce)

### 1. Pagination via nonexistent `hasMore` field
**File:** `vm_inventory_updater_fixed.py`, ~line 1014
**Wrong:** `while orders_data.get('hasMore', False) and offset < 10000:` — Clover API doesn't return `hasMore`, that's a Square/Stripe convention. Loop never fired. Busy stores (VSJ, Plaza Carolina, Plaza Las Americas) silently lost their earliest-of-day orders past the 1000-record `limit`.
**Right:** Track `last_page_size`; paginate while it equals `page_size` (1000). Stop when a page returns smaller.

### 2. Fuzzy "same-flavor, different letter" cross-routing
**File:** `vm_inventory_updater_fixed.py`, `find_cookie_row()`
**Wrong:** When the menu transitioned (K-Strawberry → E-Strawberry), the old `*K* Strawberry Cheesecake` items still selling on Clover got cleaned to `K - Strawberry Cheesecake`, didn't find a K-Strawberry slot on the sheet, then matched the E-Strawberry slot via "same flavor different letter" or substring keyword match. A subsequent write for the correct E cookie or for `*K* Vanilla Coconut Cream` (whose keyword `cream` substring-matched `C - Cookies & Cream`) **overwrote** the correct value.
**Right:** Enforce same-letter constraint in every match strategy. If Clover letter X has no sheet slot, drop the sale (caller should hide the item on POS).

### 3. `clean_cookie_name` substring-remap of canonical labels
**File:** `vm_inventory_updater_fixed.py`, top of `clean_cookie_name()`
**Wrong:** The obsolete `name_mapping` dict has historical entries like `"Strawberry Cheesecake": "K - Strawberry Cheesecake"`. The substring loop `if api_pattern.lower() in cleaned.lower(): return sheet_name` matched a sheet label `"E - Strawberry Cheesecake"` against the old `"Strawberry Cheesecake"` key and **remapped it to `K - Strawberry Cheesecake"`**. The downstream validation loop then thought row E "wasn't in the Clover cookie category" and **cleared the cell on every backfill run**.
**Right:** Fast-path at the top of `clean_cookie_name`: if input matches `^[A-Z]\s-\s[A-Za-z]` and has no `*` or `☆`, return it unchanged. Sheet labels are already canonical; don't push them through old menu-mapping.

### 4. Validation loop compared cleaned strings (`&` vs `and`)
**File:** `vm_inventory_updater_fixed.py`, ~line 2114
**Wrong:** Compared `clean_cookie_name(sheet_row)` against `allowed_sheet_names` (set built from Clover items). When sheet said `"P - Black and White"` and Clover said `*P* Black & White ☆` → cleaned strings differed, validation cleared the row.
**Right:** Compare by **letter slot only**, not full string. Build `allowed_letters` set from `allowed_sheet_names`; clear a sheet row only if its letter doesn't appear in `allowed_letters`.

### 5. `find_cookie_row` flavor match failed on `&` ↔ `and`
**File:** `vm_inventory_updater_fixed.py`, `find_cookie_row()`, same-letter flavor match path
**Right:** Normalise both sides via `s.replace(' & ', ' and ')` before comparing.

### 6. Morning PARs H formula didn't normalise `&` ↔ `and` either
**File:** Morning PARs sheet (`1g9GCvm3xRziQCG03LIL9djk9drAdABXCYPioAtuU0zE`), H column on every tab
**Wrong:** `REGEXREPLACE(headers, ..., "[^a-z0-9]", "")` stripped `&` → `blackwhite`, but `and` survived → `blackandwhite`. Lookup missed by 4 chars.
**Right:** Pre-strip `&` and the word `and` (case-insensitive) before the alphanumeric strip:
```
REGEXREPLACE(REGEXREPLACE(REGEXREPLACE(headers, "(?i)\band\b|&", ""), "...", ""), "[^a-z0-9]", "")
```

### 7. Morning PARs F-column BV fallback (since reverted)
**Context:** Earlier in the conversation we added "if BW (Ending Inv) empty, fall back to BV (Expected Live Inv)". User later reverted because BV values were unreliable (chronic negatives from missed Opening Stock). F now reads BW only via `IFERROR(..., 0)`. If team forgets BW, F shows 0; the bake formula treats as zero stock (intentional — keeps team accountable for filling BW).

### 8. Sale Report 2026 monthly rollover
**File:** Sale Report 2026 sheet weekly tabs (e.g. `May 2 - May 8`), rows 28-43 cols B-E
**Wrong:** When the team copies a tab to make a new week, the IMPORTRANGE URL stays pointed at the previous month's Dispatch PARs. First fully-May-week tab silently returns 0s, cascading to `#DIV/0!` in the %Website columns.
**Right:** When you see this, swap the URL across all 64 formulas (B28:E43). Or better: make the formula route by `MONTH($B$26)` (not yet done).

### 9. Morning PARs revert wrote rows 5-18 only
**Wrong:** Initial revert script wrote F5:F18 — but Morning PARs cookies start at **row 3** (A=row 3, B=4, …, P=18). Rows 3 and 4 kept their old BV-fallback formula. F3/F4 showed phantom values from BV until caught.
**Right:** Cookie data rows on Morning PARs are **3 through 18**, total row at 19. Use this range when touching any per-cookie column.

### 10. May 5-8 J row typo
A team member manually typed `J-Linzer` into A12 of 5-8 Mall PARs as a workaround for Linzer Cake still selling. Restored to `[NOT IN USE]`. Reminder for the team: don't edit column A labels directly — the inventory-updater matches by name, so any typo causes 0 sales to be written there.

---

## Open / known but accepted

### A. Drunken Cookies sheet has duplicate columns
Columns P/Q/R/S of every tab repeat L/M/N/O headers. Harmless because the MATCH lookup returns the first hit. Removing them risks breaking dependent VLOOKUP formulas elsewhere. Leave alone unless asked.

### B. Outdated column J header (`I - Guava Crumble`)
The column has real Guava Crumble history from 2024-2025. Renaming would misrepresent old data. Current I (Oatmeal Cream Pie) writes to flavor-only column BC (`Oatmeal Cream Pie`), which the H formula matches correctly by flavor.

### C. Triple-write in Drunken Cookies (e.g. col AY duplicates col I for Brookie with Nutella)
Updater writes the same flavor to multiple columns. Harmless for forecasts (first hit wins) but inflates if anyone sums whole rows. Don't sum unfiltered Drunken Cookies columns.

### D. VSJ chronic negative `BV` (Expected Live Inv)
Caused by team missing Opening Stock (BT) entries. ~186 negative cells across April 2026 alone. Not something the code can fix; team operational issue. The BW-only F formula on Morning PARs accepts this risk.

### E. Avast HTTPS scanning intercepts TLS on user's machine
See `CLAUDE.md` for the certifi-append workaround. Necessary on the user's Windows machine but irrelevant in Cloud Run.

### F. Oatmeal Cream Pie forecast uses default `48` until 4 Sundays accumulate
By design. Will self-resolve mid-June. If the team wants a custom default earlier, edit `standard_val` in the H formula on Morning PARs.

---

## Hot zones (if you must edit, test carefully)

- `vm_inventory_updater_fixed.py` lines ~1010–1040 (pagination), ~1115–1135 (date filter), ~2114–2145 (validation/clear), ~2415–2475 (`clean_cookie_name`), ~2735–2820 (`find_cookie_row`)
- Morning PARs H formula on any May tab (cross-sheet IMPORTRANGE, LET/LAMBDA, REGEXREPLACE chain — gets ugly)
- Sale Report 2026 weekly tab IMPORTRANGE rows 28-43
- Mall PARs row 19 (TOTAL) — chain formulas of the form `=B+D`, `=E+G-F-SUM(J:N)` etc. Easy to accidentally clobber when batch-clearing.
