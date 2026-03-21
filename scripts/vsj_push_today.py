#!/usr/bin/env python3
"""
One-off helper: Fetch VSJ cookie sales for today-so-far (PR time) from Clover,
consolidate to sheet cookie names, and write to the 9-4 tab's Old San Juan 'Live Data' column.

Run on VM:
  /opt/inventory-updater/venv/bin/python /home/banzo/vsj_push_today.py
"""
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SHEET_ID = "1zR0tPkqxMOijgQsmjLvg0cN2MlUuHlCB5VgNbNv3grU"
TAB = "9-4"
SA_PATH = "/opt/inventory-updater/service-account-key.json"
CLOVER_CREDS = "/opt/inventory-updater/secrets/clover_creds.json"


def pr_today_range_ms():
    tz = ZoneInfo("America/Puerto_Rico")
    now = datetime.now(tz)
    start = int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    end = int(now.timestamp() * 1000)
    return start, end


def fetch_vsj_counts():
    creds = json.load(open(CLOVER_CREDS))
    vsj = [c for c in creds if c.get("name") == "VSJ"][0]
    merchant_id = vsj["id"]
    token = vsj["token"]

    start, end = pr_today_range_ms()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
    params = {"filter": f"createdTime>={start}", "expand": "lineItems", "limit": 1000}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    orders = resp.json().get("elements", [])

    non_cookie_keywords = [
        "shot glass",
        "mini shot",
        "mini shots",
        "shots",
        "ice cream",
        "milk",
        "martini",
        "irish cream",
        "mocha",
        "alcohol",
        "drink",
        "latte",
        "shake",
        "store",
        "empty",
        "jalda",
    ]

    counts = {}
    for order in orders:
        created = order.get("createdTime", 0)
        if not (start <= created <= end):
            continue
        if order.get("state") not in ["locked", "paid", "completed", "open"]:
            continue
        line_items = order.get("lineItems", {}).get("elements", [])
        for li in line_items:
            if li.get("refunded") is True or li.get("exchanged") is True or li.get("isRevenue") is False:
                continue
            q = li.get("quantity")
            if q is None:
                q = 1
            if q <= 0:
                continue
            name = li.get("name", "")
            nlc = name.lower().strip()
            if re.match(r"^[A-Z]:", name.strip()):
                continue
            if any(k in nlc for k in non_cookie_keywords):
                continue
            looks_cookie = name.startswith("*") or any(
                w in nlc
                for w in [
                    "cookie",
                    "brownie",
                    "s'mores",
                    "cheesecake",
                    "churro",
                    "tres leches",
                    "lemon",
                    "strawberry",
                    "white chocolate",
                    "nutella",
                    "midnight",
                ]
            )
            if looks_cookie:
                counts[name] = counts.get(name, 0) + q
    return counts


def clean_cookie(name: str) -> str:
    if not name:
        return ""
    s = name.strip()
    if s.startswith("*") and "*" in s[1:]:
        k = s.find("*", 1)
        if k != -1:
            s = s[k + 1 :].strip()
    s = "".join(ch for ch in s if ord(ch) < 128)
    s = " ".join(s.split())
    return s


MAP_EXACT = {
    "Cookies & Cream": "Cookies & Cream",
    "Chocolate Chip Nutella": "Chocolate Chip Nutella",
    "Signature Chocolate Chip": "Signature Chocolate Chip",
    "Fudge Brownie": "Fudge Brownie",
    "Churro with Dulce De Leche": "Churro with Dulce De Leche",
    "Strawberry Cheesecake": "Strawberry Cheesecake",
    "White Chocolate Macadamia": "White Chocolate Macadamia",
    "Tres Leches": "Tres Leches",
    "Midnight with Nutella": "Midnight with Nutella",
    "S'mores": "S'mores",
    "Lemon Poppyseed": "Lemon Poppyseed",
    "Cheesecake with Biscoff": "Cheesecake with Biscoff",
}


def consolidate(counts_raw: dict) -> dict:
    out = {}
    for name, q in counts_raw.items():
        base = clean_cookie(name)
        for k, v in MAP_EXACT.items():
            if k.lower() in base.lower():
                base = v
                break
        out[base] = out.get(base, 0) + q
    return out


def column_to_letter(idx: int) -> str:
    result = ""
    while idx >= 0:
        result = chr(65 + (idx % 26)) + result
        idx = idx // 26 - 1
    return result


def write_to_sheet(consolidated: dict):
    creds = Credentials.from_service_account_file(
        SA_PATH, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    svc = build("sheets", "v4", credentials=creds)

    values = (
        svc.spreadsheets()
        .values()
        .get(spreadsheetId=SHEET_ID, range=f"{TAB}!A:CC")
        .execute()
        .get("values", [])
    )
    location_row = values[0]
    headers = values[1]
    cookie_rows = [row[0] for row in values[2:20] if row and row[0]]

    osj_col = None
    for i, header in enumerate(headers):
        if "live data" in str(header).lower():
            if i < len(location_row) and location_row[i] and "Old San Juan" in location_row[i]:
                osj_col = i
                break
    if osj_col is None:
        print("NO_OSJ_COLUMN")
        return

    row_for = {}
    for i, cookie in enumerate(cookie_rows, start=3):
        base = cookie.split(" - ", 1)[1].strip() if " - " in cookie else cookie
        row_for[base] = i

    updates = []
    for base, count in consolidated.items():
        r = row_for.get(base)
        if not r:
            continue
        rng = f"{TAB}!{column_to_letter(osj_col)}{r}"
        updates.append({"range": rng, "values": [[str(count)]]})

    if not updates:
        print("NO_UPDATES", consolidated)
        return

    svc.spreadsheets().values().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={"valueInputOption": "RAW", "data": updates},
    ).execute()
    print("UPDATED", len(updates), "cells", consolidated)


def main():
    raw = fetch_vsj_counts()
    consolidated = consolidate(raw)
    write_to_sheet(consolidated)


if __name__ == "__main__":
    main()











