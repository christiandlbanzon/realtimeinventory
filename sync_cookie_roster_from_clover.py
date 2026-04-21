#!/usr/bin/env python3
"""
Sync cookie flavor labels from Clover's Cookies category into Google Sheets.

Why this exists:
- Category membership (allowed_item_ids) is already automatic for *counting*.
- **Mall PARs** (1st) column A; **Dispatch PARs** (2nd) stacked blocks; **Morning PARs** (3rd) same
  layout as Mall — run ``--targets mall_pars,dispatch_pars,morning_pars`` (scheduled defaults match).
  Set ``MORNING_PARS_SHEET_ID`` / ``DISPATCH_PARS_SHEET_ID`` when the monthly v2 files change.
- **Drunken Cookies**: the inventory updater (``vm_inventory_updater``) already **appends new
  flavor columns** when sales appear for unknown names. Use ``--targets drunken`` only when you
  intentionally want row 1 **replaced** with fixed Date + A–N + ``[NOT IN USE]``; that can
  conflict with manually appended columns.

Usage (dry-run, prints roster + diffs):
  python sync_cookie_roster_from_clover.py --location VSJ

Apply Mall PARs column A (primary): fixed slots A–N (rows 3–16), two ``[NOT IN USE]`` rows (17–18), TOTAL unchanged.
  python sync_cookie_roster_from_clover.py --location VSJ --apply --targets mall_pars \\
    --mall-pars-sheet-id YOUR_SHEET_ID --mall-pars-tab 3-27

**Dispatch PARs** (``v2 … Dispatch PARs_2026``): same A–N labels in **column A**, repeated for each
mall block **stacked vertically** — row 1 = ``PARs for:`` / date; row 2 = first location header;
cookie rows for block 0 = rows 3–18; then totals row; next block every ``DISPATCH_BLOCK_STRIDE`` rows
(default 18). Optional ``--targets dispatch_pars`` with ``--dispatch-pars-sheet-id`` and
``--dispatch-pars-tab`` (same ``M-D`` tab as Mall PARs).

Optional — overwrite Drunken Cookies row 1 on all store tabs (fixed A–N layout):
  python sync_cookie_roster_from_clover.py --location VSJ --apply --targets drunken

Safety: default is dry-run. --apply performs writes. Use one canonical Clover location
whose catalog matches your sheets (often VSJ or the "main" merchant).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import random
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Reuse canonical naming + category fetch from the main job (Docker: vm_inventory_updater_fixed.py).
from vm_inventory_updater_fixed import (
    clean_cookie_name,
    column_to_letter,
    enrich_item_flags_for_ids,
    fetch_clover_category_items,
)

DRUNKEN_COOKIES_SHEET_ID = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"
DRUNKEN_TABS = ["Plaza", "PlazaSol", "San Patricio", "VSJ", "Montehiedra", "Plaza Carolina"]

# Mall PARs: one row per letter A–N (rows 3–16), then two "[NOT IN USE]" spacer rows (17–18), then TOTAL (19).
# Clover updates fill by letter only — no duplicate letters, unused letters stay "[NOT IN USE]".
MALL_PARS_LETTER_SLOTS = "ABCDEFGHIJKLMN"
MALL_PARS_AFTER_LETTER_PLACEHOLDERS = 2

# Dispatch PARs (v2): one sheet tab per day; column A only for cookie names. Layout per block:
#   Row 0 of block = location name (e.g. "San Patricio") + metric headers in B…
#   Next 16 rows = same as Mall PARs column A (A–N + two "[NOT IN USE]").
#   Then one totals row (often numeric in column A, not the word "TOTAL").
# Blocks repeat every DISPATCH_BLOCK_STRIDE rows (default 18): row-2 headers at 2, 20, 38, …
# Default sheet: v2 March Dispatch PARs_2026 (override with --dispatch-pars-sheet-id).
DISPATCH_PARS_DEFAULT_SHEET_ID = "1XC9o3iGhv2YWAXZqnDwz0bxA1N4kJKkn_fswiz7X6ek"
DISPATCH_BLOCK_FIRST_COOKIE_ROW = 3  # first block cookie rows start at A3
DISPATCH_BLOCK_STRIDE = 18  # header + 16 cookie rows + 1 totals row
DISPATCH_LOCATION_HEADERS_DEFAULT = (
    "San Patricio",
    "Plaza del Sol",
    "Montehiedra",
    "Plaza Carolina",
    "Plaza Las Americas",
)

# Morning PARs (v2): single block, same column A layout as Mall PARs (rows 3–18, then Total).
# Default: v2 March Morning PARs_2026 — set MORNING_PARS_SHEET_ID when the monthly file changes.
MORNING_PARS_DEFAULT_SHEET_ID = "1BbZc3DYa3r0aCR2jiwm6ecs7cs7v4IRO39nHFIYR1oc"

# Clover often has multiple category items that map to the same letter (old + new flavors).
# Tie-break order: (1) raw *Letter* POS line, (2) hidden/available, (3) keyword list,
# (4) generic *Letter* style, (5) A–Z by canonical name.
# Clover field `hidden`: False = shown on Register (Show on POS on); True = hidden from POS.
LETTER_PREFERENCE_ORDER: Dict[str, List[str]] = {
    # E: Churro is the active *E* slot flavor; Strawberry Cheesecake moved to *K* in POS.
    "E": ["churro", "dulce de leche", "strawberry cheesecake", "strawberry"],
    "F": ["brookie", "almond"],
    "G": ["sticky toffee", "sticky", "pecan"],
    "I": ["guava", "tres leches"],
    # K: Prefer Strawberry Cheesecake when both K-slot items exist (matches *K* / *K^ on Clover).
    "K": ["strawberry cheesecake", "strawberry", "vanilla coconut"],
}


def _sheets_execute_with_retry(request, max_retries: int = 5, base_delay: float = 5.0):
    """Execute a Google Sheets API request with retry on 429 rate-limit errors."""
    from googleapiclient.errors import HttpError

    for attempt in range(max_retries + 1):
        try:
            return request.execute()
        except HttpError as e:
            if e.resp.status == 429 and attempt < max_retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logging.warning(
                    "Sheets API rate limited (429). Retrying in %.1fs (attempt %d/%d)",
                    delay, attempt + 1, max_retries,
                )
                time.sleep(delay)
                continue
            raise


def _ensure_tab_exists(service, spreadsheet_id: str, title: str) -> bool:
    """Create a tab if it doesn't already exist. Returns True if a new tab was created."""
    sid = _sheet_id_for_title(service, spreadsheet_id, title)
    if sid is not None:
        return False
    logging.info("Tab '%s' not found — creating it.", title)
    _sheets_execute_with_retry(
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
        )
    )
    return True


def _sheet_id_for_title(service, spreadsheet_id: str, title: str) -> Optional[int]:
    meta = _sheets_execute_with_retry(
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, fields="sheets(properties(sheetId,title))")
    )
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == title:
            return s["properties"]["sheetId"]
    return None


def _grid_get_values_col_a(
    service, spreadsheet_id: str, sheet_numeric_id: int, row_1_start: int, row_1_end_inclusive: int
) -> List[List]:
    """Read column A for 1-based inclusive row range. Uses gridRange so tab titles like 4-1 / 04-01 work."""
    if row_1_end_inclusive < row_1_start:
        return []
    body = {
        "dataFilters": [
            {
                "gridRange": {
                    "sheetId": sheet_numeric_id,
                    "startRowIndex": row_1_start - 1,
                    "endRowIndex": row_1_end_inclusive,
                    "startColumnIndex": 0,
                    "endColumnIndex": 1,
                }
            }
        ],
        "majorDimension": "ROWS",
    }
    r = _sheets_execute_with_retry(
        service.spreadsheets().values().batchGetByDataFilter(
            spreadsheetId=spreadsheet_id, body=body
        )
    )
    vrs = r.get("valueRanges") or []
    if not vrs:
        return []
    return (vrs[0].get("valueRange") or {}).get("values") or []


def _grid_update_col_a(
    service, spreadsheet_id: str, sheet_numeric_id: int, row_1_start: int, values: List[List[str]]
) -> None:
    """Write column A starting at row_1_start; values is N rows × 1 column."""
    n = len(values)
    if n == 0:
        return
    rows = [
        {"values": [{"userEnteredValue": {"stringValue": (r[0] if r else "")}}]} for r in values
    ]
    _sheets_execute_with_retry(
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {
                        "updateCells": {
                            "range": {
                                "sheetId": sheet_numeric_id,
                                "startRowIndex": row_1_start - 1,
                                "endRowIndex": row_1_start - 1 + n,
                                "startColumnIndex": 0,
                                "endColumnIndex": 1,
                            },
                            "rows": rows,
                            "fields": "userEnteredValue",
                        }
                    }
                ]
            },
        )
    )


def _find_total_row_col_a(service, sheet_id: str, tab: str) -> Optional[int]:
    """
    Mall PARs tabs have a TOTAL row in column A. Roster sync must not overwrite it.
    Returns 1-based row index or None if not found.
    """
    sid = _sheet_id_for_title(service, sheet_id, tab)
    if sid is None:
        return None
    vals = _grid_get_values_col_a(service, sheet_id, sid, 3, 200)
    for i, row in enumerate(vals):
        if not row:
            continue
        raw = str(row[0]).strip()
        u = raw.upper()
        if u == "TOTAL" or u.startswith("TOTAL ") or u == "TOTAL:":
            return i + 3
    return None


def _expected_first_total_row_mall_pars() -> int:
    """First row where TOTAL should appear for the fixed A–N + 2 placeholder layout."""
    return 3 + len(MALL_PARS_LETTER_SLOTS) + MALL_PARS_AFTER_LETTER_PLACEHOLDERS


def _clover_name_leading_letter(raw: str) -> bool:
    """True when the API name looks like POS *E* Flavor (leading *Letter*)."""
    s = (raw or "").strip()
    return bool(re.match(r"^\*\s*[A-Za-z]\s*\*", s))


def _raw_matches_pos_letter_slot(raw: str, letter: str) -> bool:
    """
    True when the raw Clover item name is the active Register line for that slot:
    *E* Flavor (literal letter between stars), or *K^* caret variant — not *_* legacy rows.
    """
    s = (raw or "").strip()
    if len(letter) != 1:
        return False
    L = letter.upper()
    if re.match(rf"^\*\s*{re.escape(L)}\s*\*", s):
        return True
    if re.match(rf"^\*\s*{re.escape(L)}\s*\^", s, re.IGNORECASE):
        return True
    return False


def _pick_canonical_for_letter(
    letter: str,
    entries: List[Tuple[str, str, str]],
    id_to_flags: Dict[str, dict],
) -> str:
    """entries: (item_id, raw_clover_name, canonical)."""
    orig = list(entries)

    def flags(iid: str) -> dict:
        return id_to_flags.get(iid) or {}

    pool = list(entries)

    # 0) Prefer raw *Letter* (e.g. *E* Strawberry) — that is the active POS slot line in Clover.
    # Rows like *_* Churro* still map to E - … in clean_cookie_name but are not the *E* Register line.
    slot_matches = [e for e in orig if _raw_matches_pos_letter_slot(e[1], letter)]
    if len(slot_matches) == 1:
        logging.info(
            "Letter %s: chose %r (raw *%s* POS slot; %d Clover items)",
            letter,
            slot_matches[0][2],
            letter.upper(),
            len(orig),
        )
        return slot_matches[0][2]
    if len(slot_matches) > 1:
        pool = slot_matches
    # else: no *Letter* raw — keep full pool (legacy / odd merchants)

    # 1) Prefer not hidden (visible on Register = Show on POS on)
    if any(flags(e[0]).get("hidden") is not None for e in pool):

        def rank_hidden(e: Tuple[str, str, str]) -> int:
            h = flags(e[0]).get("hidden")
            if h is False:
                return 0
            if h is None:
                return 1
            return 2

        best = min(rank_hidden(e) for e in pool)
        nxt = [e for e in pool if rank_hidden(e) == best]
        if nxt:
            pool = nxt
    if not pool:
        pool = orig

    # 2) Prefer available=True (saleable)
    if any(flags(e[0]).get("available") is not None for e in pool):

        def rank_avail(e: Tuple[str, str, str]) -> int:
            a = flags(e[0]).get("available")
            if a is True:
                return 0
            if a is None:
                return 1
            return 2

        best = min(rank_avail(e) for e in pool)
        nxt = [e for e in pool if rank_avail(e) == best]
        if nxt:
            pool = nxt
    if not pool:
        pool = orig

    # 3) Keyword preferences BEFORE POS-style filter: Clover sometimes sends *_* Churro (no *E*)
    # while another row is *E* Strawberry — leading-* filter would drop Churro and skip keywords.
    for pref in LETTER_PREFERENCE_ORDER.get(letter, []):
        pl = pref.lower()
        for e in pool:
            blob = f"{e[1]} {e[2]}".lower()
            if pl in blob:
                logging.info(
                    "Letter %s: chose %r (keyword %r; %d Clover items)",
                    letter,
                    e[2],
                    pref,
                    len(orig),
                )
                return e[2]

    # 4) Prefer names that start with *Letter* like the live POS list
    if any(_clover_name_leading_letter(e[1]) for e in pool):
        pool = [e for e in pool if _clover_name_leading_letter(e[1])]
    if not pool:
        pool = orig

    chosen = sorted(pool, key=lambda x: x[2].lower())[0][2]
    logging.warning(
        "Letter %s: fallback to alphabetically first %r (%d candidates)",
        letter,
        chosen,
        len(orig),
    )
    return chosen


def _by_letter_from_clover(creds: dict) -> Dict[str, str]:
    """
    One sheet label per letter A–N from Clover category items.
    Duplicates: raw *Letter* slot, then hidden/available, keywords, POS-style names, A–Z.
    """
    _, id_to_name, id_to_flags = fetch_clover_category_items(creds)
    if not id_to_name:
        raise SystemExit(
            "Category returned no items. Check merchant token, cookie_category_id, and API access."
        )
    letter_groups: dict[str, List[Tuple[str, str, str]]] = defaultdict(list)
    seen_ids: set[str] = set()
    for iid, raw in id_to_name.items():
        raw = (raw or "").strip()
        if not raw or iid in seen_ids:
            continue
        seen_ids.add(iid)
        canon = clean_cookie_name(raw)
        if not canon:
            continue
        m = re.match(r"^([A-Za-z])\s*-\s*", canon.strip())
        if not m:
            continue
        letter = m.group(1).upper()
        if letter not in MALL_PARS_LETTER_SLOTS:
            logging.warning(
                "Letter %s not in Mall PARs slots %s — add slot or remove item: %r",
                letter,
                MALL_PARS_LETTER_SLOTS,
                canon,
            )
            continue
        letter_groups[letter].append((iid, raw, canon))

    # Fetch hidden/available flags for ALL items so we can filter strictly
    all_ids = [iid for entries in letter_groups.values() for iid, _, _ in entries]
    if all_ids:
        enrich_item_flags_for_ids(creds, all_ids, id_to_flags)

    by: Dict[str, str] = {}
    for letter in MALL_PARS_LETTER_SLOTS:
        entries = letter_groups.get(letter, [])
        if not entries:
            continue
        # Strictly filter out items where Show on POS is OFF (hidden=True)
        active = [e for e in entries if id_to_flags.get(e[0], {}).get("hidden") is not True]
        if not active:
            logging.info("Letter %s: all %d items hidden on POS — marking [NOT IN USE]", letter, len(entries))
            continue
        if len(active) == 1:
            by[letter] = active[0][2]
        else:
            by[letter] = _pick_canonical_for_letter(letter, active, id_to_flags)
    return by


def _mall_pars_column_a_values(by_letter: dict[str, str]) -> List[List[str]]:
    """Rows 3–18: A–N slots + two [NOT IN USE] spacers before TOTAL."""
    rows: List[List[str]] = []
    for L in MALL_PARS_LETTER_SLOTS:
        rows.append([by_letter.get(L, "[NOT IN USE]")])
    for _ in range(MALL_PARS_AFTER_LETTER_PLACEHOLDERS):
        rows.append(["[NOT IN USE]"])
    return rows


def _drunken_header_row_from_by_letter(by_letter: Dict[str, str]) -> List[str]:
    """Same A–N letter slots as Mall PARs: Date + one column per letter (unused = [NOT IN USE])."""
    return ["Date"] + [by_letter.get(L, "[NOT IN USE]") for L in MALL_PARS_LETTER_SLOTS]


def _mall_pars_layout_ok(service, sheet_id: str, tab: str) -> bool:
    """TOTAL must be at or below the first row after the fixed block (not inside rows 3–18)."""
    tr = _find_total_row_col_a(service, sheet_id, tab)
    need = _expected_first_total_row_mall_pars()
    if tr is None:
        logging.warning("Mall PARs tab '%s': no TOTAL in column A — writing rows 3–18 anyway.", tab)
        return True
    if tr < need:
        logging.error(
            "Mall PARs tab '%s': TOTAL is at row %s but must be at row %s or later "
            "(rows 3–%s are fixed A–N + spacers). Move TOTAL down or fix the tab.",
            tab,
            tr,
            need,
            need - 1,
        )
        return False
    return True


def _load_clover_cred(location: str) -> dict:
    with open("clover_creds.json", encoding="utf-8") as f:
        rows = json.load(f)
    for row in rows:
        name = row.get("name") or row.get("location")
        if name == location:
            return row
    raise SystemExit(f"No Clover credential with name/location '{location}' in clover_creds.json")


def _roster_from_category(creds: dict) -> List[str]:
    _, id_to_name, _ = fetch_clover_category_items(creds)
    if not id_to_name:
        raise SystemExit(
            "Category returned no items. Check merchant token, cookie_category_id, and API access."
        )
    seen = set()
    out: List[str] = []
    for _iid, raw in sorted(id_to_name.items(), key=lambda x: (x[1] or "").lower()):
        canon = clean_cookie_name(raw)
        if not canon or canon in seen:
            continue
        seen.add(canon)
        out.append(canon)

    def sort_key(n: str) -> Tuple[str, str]:
        m = re.match(r"^([A-Za-z])\s*-\s*", n.strip())
        letter = (m.group(1).upper() if m else "~")
        return (letter, n.lower())

    out.sort(key=sort_key)
    return out


def _dry_run_drunken(service, by_letter: Dict[str, str]) -> None:
    meta = _sheets_execute_with_retry(
        service.spreadsheets().get(spreadsheetId=DRUNKEN_COOKIES_SHEET_ID)
    )
    titles = {s["properties"]["title"] for s in meta.get("sheets", [])}
    want = _drunken_header_row_from_by_letter(by_letter)
    for tab in DRUNKEN_TABS:
        if tab not in titles:
            logging.warning("Tab missing (skip): %s", tab)
            continue
        res = _sheets_execute_with_retry(
            service.spreadsheets()
            .values()
            .get(spreadsheetId=DRUNKEN_COOKIES_SHEET_ID, range=f"'{tab}'!1:1")
        )
        row = (res.get("values") or [[]])[0]
        if row == want:
            logging.info("Drunken [%s]: row 1 already matches (%d cols).", tab, len(want))
        else:
            logging.info("Drunken [%s]: would set %d header columns (first mismatch if any).", tab, len(want))
            for i, (a, b) in enumerate(zip(want, row + [""] * len(want))):
                if i >= len(row) or a != row[i]:
                    logging.info("  first diff at col %s: want %r have %r", column_to_letter(i), a, row[i] if i < len(row) else "")
                    break


def _apply_drunken(service, by_letter: Dict[str, str]) -> None:
    want = _drunken_header_row_from_by_letter(by_letter)
    end_letter = column_to_letter(len(want) - 1)
    range_a1 = f"A1:{end_letter}1"
    meta = _sheets_execute_with_retry(
        service.spreadsheets().get(spreadsheetId=DRUNKEN_COOKIES_SHEET_ID)
    )
    titles = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta.get("sheets", [])}
    for tab in DRUNKEN_TABS:
        if tab not in titles:
            logging.warning("Tab missing (skip): %s", tab)
            continue
        sid = titles[tab]
        grid = 0
        for s in meta.get("sheets", []):
            if s["properties"]["title"] == tab:
                grid = s.get("properties", {}).get("gridProperties", {}).get("columnCount", 0)
                break
        if grid and len(want) > grid:
            _sheets_execute_with_retry(
                service.spreadsheets().batchUpdate(
                    spreadsheetId=DRUNKEN_COOKIES_SHEET_ID,
                    body={
                        "requests": [
                            {
                                "appendDimension": {
                                    "sheetId": sid,
                                    "dimension": "COLUMNS",
                                    "length": len(want) - grid,
                                }
                            }
                        ]
                    },
                )
            )
            logging.info("Expanded grid on %s by %d columns", tab, len(want) - grid)
        _sheets_execute_with_retry(
            service.spreadsheets().values().update(
                spreadsheetId=DRUNKEN_COOKIES_SHEET_ID,
                range=f"'{tab}'!{range_a1}",
                valueInputOption="USER_ENTERED",
                body={"values": [want]},
            )
        )
        logging.info("Updated Drunken Cookies tab %s row 1 (%d columns).", tab, len(want))


def _dry_run_single_block_mall_layout(
    service, sheet_id: str, tab: str, by_letter: Dict[str, str], label: str
) -> None:
    if not _mall_pars_layout_ok(service, sheet_id, tab):
        return
    want_rows = _mall_pars_column_a_values(by_letter)
    n = len(want_rows)
    sid = _sheet_id_for_title(service, sheet_id, tab)
    if sid is None:
        logging.error("%s: tab %r not found in spreadsheet.", label, tab)
        return
    vals = _grid_get_values_col_a(service, sheet_id, sid, 3, 2 + n)
    cols = [r[0] if r else "" for r in vals]
    for i, row in enumerate(want_rows):
        want = row[0]
        cur = cols[i] if i < len(cols) else ""
        if (cur or "").strip() != (want or "").strip():
            logging.info("%s row %d: want %r have %r", label, i + 3, want, cur)


def _apply_single_block_mall_layout(
    service, sheet_id: str, tab: str, by_letter: Dict[str, str], label: str
) -> None:
    _ensure_tab_exists(service, sheet_id, tab)
    if not _mall_pars_layout_ok(service, sheet_id, tab):
        return
    want_rows = _mall_pars_column_a_values(by_letter)
    n = len(want_rows)
    sid = _sheet_id_for_title(service, sheet_id, tab)
    if sid is None:
        logging.error("%s: tab %r not found in spreadsheet.", label, tab)
        return
    _grid_update_col_a(service, sheet_id, sid, 3, want_rows)
    logging.info(
        "Updated %s %s tab %s rows 3-%d (fixed A–N letter slots + spacers), TOTAL row unchanged.",
        label,
        sheet_id[:12],
        tab,
        2 + n,
    )


def _dry_run_mall_pars(service, sheet_id: str, tab: str, by_letter: Dict[str, str]) -> None:
    _dry_run_single_block_mall_layout(service, sheet_id, tab, by_letter, "Mall PARs")


def _apply_mall_pars(service, sheet_id: str, tab: str, by_letter: Dict[str, str]) -> None:
    _apply_single_block_mall_layout(service, sheet_id, tab, by_letter, "Mall PARs")


def _dry_run_morning_pars(service, sheet_id: str, tab: str, by_letter: Dict[str, str]) -> None:
    _dry_run_single_block_mall_layout(service, sheet_id, tab, by_letter, "Morning PARs")


def _apply_morning_pars(service, sheet_id: str, tab: str, by_letter: Dict[str, str]) -> None:
    _apply_single_block_mall_layout(service, sheet_id, tab, by_letter, "Morning PARs")


def _dispatch_block_count() -> int:
    return int(os.getenv("DISPATCH_BLOCK_COUNT", str(len(DISPATCH_LOCATION_HEADERS_DEFAULT))))


def _dispatch_cookie_start_rows() -> List[int]:
    first = int(os.getenv("DISPATCH_FIRST_COOKIE_ROW", str(DISPATCH_BLOCK_FIRST_COOKIE_ROW)))
    stride = int(os.getenv("DISPATCH_BLOCK_STRIDE", str(DISPATCH_BLOCK_STRIDE)))
    n = _dispatch_block_count()
    return [first + stride * i for i in range(n)]


def _dispatch_location_headers() -> List[str]:
    raw = os.getenv("DISPATCH_LOCATION_HEADERS", "")
    if raw.strip():
        return [x.strip() for x in raw.split(",") if x.strip()]
    return list(DISPATCH_LOCATION_HEADERS_DEFAULT)


def _dispatch_verify_location_row(
    service,
    sheet_id: str,
    tab: str,
    block_index: int,
    header_row: int,
    expect: str,
    sheet_numeric_id: Optional[int] = None,
) -> bool:
    sid = sheet_numeric_id if sheet_numeric_id is not None else _sheet_id_for_title(service, sheet_id, tab)
    if sid is None:
        logging.error("Dispatch tab %r not found.", tab)
        return False
    vals = _grid_get_values_col_a(service, sheet_id, sid, header_row, header_row)
    row = vals[0] if vals else []
    got = (row[0] if row else "").strip()
    if not got:
        # Empty header row — tab is new/blank, skip verification and allow writing
        logging.info(
            "Dispatch PARs block %d: row %d is empty (new tab) — skipping header verification.",
            block_index + 1, header_row,
        )
        return True
    if got.lower() != expect.strip().lower():
        logging.error(
            "Dispatch PARs block %d: column A row %d expected location %r, got %r — "
            "fix layout or set DISPATCH_BLOCK_STRIDE / DISPATCH_FIRST_COOKIE_ROW / DISPATCH_BLOCK_COUNT.",
            block_index + 1,
            header_row,
            expect,
            got,
        )
        return False
    return True


def _dry_run_dispatch_pars(service, sheet_id: str, tab: str, by_letter: Dict[str, str]) -> None:
    want_rows = _mall_pars_column_a_values(by_letter)
    n = len(want_rows)
    starts = _dispatch_cookie_start_rows()
    headers = _dispatch_location_headers()
    skip_v = os.getenv("DISPATCH_SKIP_HEADER_VERIFY", "").strip().lower() in ("1", "true", "yes")
    if len(headers) < len(starts):
        logging.warning(
            "DISPATCH_LOCATION_HEADERS has %d entries but %d blocks — verify DISPATCH_BLOCK_COUNT.",
            len(headers),
            len(starts),
        )
    dsid = _sheet_id_for_title(service, sheet_id, tab)
    if dsid is None:
        logging.error("Dispatch tab %r not found.", tab)
        return
    for bi, start in enumerate(starts):
        hr = start - 1
        if not skip_v and bi < len(headers):
            if not _dispatch_verify_location_row(
                service, sheet_id, tab, bi, hr, headers[bi], sheet_numeric_id=dsid
            ):
                logging.warning(
                    "Dispatch block %d: location row check failed — diffs still shown.",
                    bi + 1,
                )
        vals = _grid_get_values_col_a(service, sheet_id, dsid, start, start + n - 1)
        cols = [r[0] if r else "" for r in vals]
        for i, row in enumerate(want_rows):
            want = row[0]
            cur = cols[i] if i < len(cols) else ""
            if (cur or "").strip() != (want or "").strip():
                logging.info(
                    "Dispatch PARs block %d row %d: want %r have %r",
                    bi + 1,
                    i + start,
                    want,
                    cur,
                )


def _apply_dispatch_pars(service, sheet_id: str, tab: str, by_letter: Dict[str, str]) -> bool:
    newly_created = _ensure_tab_exists(service, sheet_id, tab)
    want_rows = _mall_pars_column_a_values(by_letter)
    n = len(want_rows)
    starts = _dispatch_cookie_start_rows()
    headers = _dispatch_location_headers()
    skip_v = newly_created or os.getenv("DISPATCH_SKIP_HEADER_VERIFY", "").strip().lower() in ("1", "true", "yes")
    if len(headers) < len(starts):
        logging.warning(
            "DISPATCH_LOCATION_HEADERS has %d entries but %d blocks — verify DISPATCH_BLOCK_COUNT.",
            len(headers),
            len(starts),
        )
    dsid = _sheet_id_for_title(service, sheet_id, tab)
    if dsid is None:
        logging.error("Dispatch tab %r not found.", tab)
        return False
    for bi, start in enumerate(starts):
        hr = start - 1
        if not skip_v and bi < len(headers):
            if not _dispatch_verify_location_row(
                service, sheet_id, tab, bi, hr, headers[bi], sheet_numeric_id=dsid
            ):
                return False
        _grid_update_col_a(service, sheet_id, dsid, start, want_rows)
        logging.info(
            "Updated Dispatch PARs %s tab %s block %d column A rows %d-%d.",
            sheet_id[:12],
            tab,
            bi + 1,
            start,
            start + n - 1,
        )
    return True


def main() -> int:
    p = argparse.ArgumentParser(description="Sync cookie roster from Clover category to sheets.")
    p.add_argument("--location", default=os.getenv("SYNC_CLOVER_LOCATION", "VSJ"), help="Clover location name in clover_creds.json")
    p.add_argument("--apply", action="store_true", help="Write to sheets (default is dry-run)")
    p.add_argument(
        "--targets",
        default="drunken",
        help="Comma list: drunken, mall_pars, dispatch_pars, morning_pars (default: drunken)",
    )
    p.add_argument("--mall-pars-sheet-id", default=os.getenv("INVENTORY_SHEET_ID", ""))
    p.add_argument("--mall-pars-tab", default="", help='Tab e.g. "3-27" for Mall PARs')
    p.add_argument(
        "--dispatch-pars-sheet-id",
        default=os.getenv("DISPATCH_PARS_SHEET_ID", ""),
        help="Dispatch PARs spreadsheet id (default: v2 Dispatch PARs file if unset)",
    )
    p.add_argument(
        "--dispatch-pars-tab",
        default=os.getenv("DISPATCH_PARS_TAB", ""),
        help='Same M-D tab as Mall PARs; optional if --mall-pars-tab is set',
    )
    p.add_argument(
        "--morning-pars-sheet-id",
        default=os.getenv("MORNING_PARS_SHEET_ID", ""),
        help="Morning PARs spreadsheet id (default: v2 Morning PARs file if unset)",
    )
    p.add_argument(
        "--morning-pars-tab",
        default=os.getenv("MORNING_PARS_TAB", ""),
        help='Same M-D tab as Mall PARs; optional if --mall-pars-tab is set',
    )
    args = p.parse_args()
    targets = {t.strip().lower() for t in args.targets.split(",")}

    cred = _load_clover_cred(args.location)
    by_letter = _by_letter_from_clover(cred)
    roster = _roster_from_category(cred)
    logging.info("Canonical roster from Clover category (%d unique names):", len(roster))
    for line in roster:
        print(f"  {line}")
    logging.info("Resolved one label per letter (A–N) for sheet slots:")
    for L in MALL_PARS_LETTER_SLOTS:
        v = by_letter.get(L)
        if v:
            print(f"  {L}: {v}")

    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    gcreds = Credentials.from_service_account_file(
        "service-account-key.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    service = build("sheets", "v4", credentials=gcreds)

    if "drunken" in targets:
        if args.apply:
            _apply_drunken(service, by_letter)
        else:
            _dry_run_drunken(service, by_letter)

    if "mall_pars" in targets:
        if not args.mall_pars_sheet_id or not args.mall_pars_tab:
            logging.error("Mall PARs requires --mall-pars-sheet-id and --mall-pars-tab")
            return 1
        if args.apply:
            _apply_mall_pars(service, args.mall_pars_sheet_id, args.mall_pars_tab, by_letter)
        else:
            _dry_run_mall_pars(service, args.mall_pars_sheet_id, args.mall_pars_tab, by_letter)

    if "dispatch_pars" in targets:
        dtab = (args.dispatch_pars_tab or args.mall_pars_tab or "").strip()
        dsid = (args.dispatch_pars_sheet_id or "").strip() or DISPATCH_PARS_DEFAULT_SHEET_ID
        if not dtab:
            logging.error("dispatch_pars requires --dispatch-pars-tab or --mall-pars-tab")
            return 1
        if args.apply:
            if not _apply_dispatch_pars(service, dsid, dtab, by_letter):
                return 1
        else:
            _dry_run_dispatch_pars(service, dsid, dtab, by_letter)

    if "morning_pars" in targets:
        mtab = (args.morning_pars_tab or args.mall_pars_tab or "").strip()
        msid = (args.morning_pars_sheet_id or "").strip() or MORNING_PARS_DEFAULT_SHEET_ID
        if not mtab:
            logging.error("morning_pars requires --morning-pars-tab or --mall-pars-tab")
            return 1
        if args.apply:
            _apply_morning_pars(service, msid, mtab, by_letter)
        else:
            _dry_run_morning_pars(service, msid, mtab, by_letter)

    if not args.apply:
        logging.info("Dry-run only. Pass --apply to write sheets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
