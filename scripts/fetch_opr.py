#!/usr/bin/env python3
"""
ML Economic 1 (Ajey) - step 2: Bank Negara Malaysia OPR history.

Why this exists: api.data.gov.my carries bank retail rates (BLR/FDR) but NOT the
policy rate. BNM's Open API (/public/opr) only returns the most recent decision.
The decision history lives on BNM's site behind year "tags", so we walk them.

Output:
    data/raw/opr_decisions.csv   one row per MPC decision (date, change, new level)
    data/opr_monthly.csv         month -> OPR in force (month-end, and month mean)

Usage:  python scripts/fetch_opr.py
"""
from __future__ import annotations

import csv
import re
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

BASE = "https://www.bnm.gov.my/monetary-stability/opr-decisions"
YEARS = range(2004, datetime.now().year + 1)
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

ROW_RE = re.compile(
    r"<td[^>]*>\s*(\d{2}\s+[A-Z][a-z]{2}\s+\d{4})\s*</td>\s*"
    r"<td[^>]*>\s*([+\-]?\d+(?:\.\d+)?)\s*</td>\s*"
    r"<td[^>]*>\s*(\d+(?:\.\d+)?)\s*</td>",
    re.S,
)


HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE,
}


def fetch_year(year: int, attempts: int = 4) -> list[dict]:
    """BNM's WAF intermittently 403s; retry with backoff before giving up."""
    url = f"{BASE}/-/tag/opr-{year}"
    last: Exception | None = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            break
        except Exception as exc:                      # noqa: BLE001
            last = exc
            time.sleep(2.5 * (i + 1))
    else:
        raise RuntimeError(f"all {attempts} attempts failed: {last}")

    rows = []
    for d, chg, lvl in ROW_RE.findall(html):
        day, mon, yr = d.split()
        if int(yr) != year:
            continue
        rows.append({
            "decision_date": date(int(yr), MONTHS[mon], int(day)).isoformat(),
            "change_pp": float(chg),
            "new_level_pct": float(lvl),
        })
    return rows


def main() -> None:
    decisions: dict[str, dict] = {}
    failed: list[int] = []
    for y in YEARS:
        try:
            got = fetch_year(y)
        except Exception as exc:                      # noqa: BLE001
            print(f"  {y}: FAILED ({exc})")
            failed.append(y)
            continue
        print(f"  {y}: {len(got):2d} decisions")
        for r in got:
            decisions[r["decision_date"]] = r
        time.sleep(1.2)

    # A missing year silently shifts the whole stepped series (an absent cut looks
    # like the old rate persisting). Refuse to publish an incomplete history.
    hard_fail = [y for y in failed if y >= 2015]
    if hard_fail:
        raise SystemExit(
            f"missing OPR years {hard_fail} - refusing to build a stepped series "
            f"from incomplete decisions. Re-run (WAF 403s are intermittent).")
    if failed:
        print(f"  note: years {failed} unavailable (pre-2015, outside the panel)")

    rows = [decisions[d] for d in sorted(decisions)]
    if not rows:
        raise SystemExit("no OPR decisions parsed - page layout changed?")

    out = RAW / "opr_decisions.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["decision_date", "change_pp", "new_level_pct"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out.relative_to(ROOT)} ({len(rows)} decisions, "
          f"{rows[0]['decision_date']} -> {rows[-1]['decision_date']})")

    # ---- expand to a daily stepped series, then to monthly ----------------
    start = datetime.fromisoformat(rows[0]["decision_date"]).date()
    end = date.today()
    level = rows[0]["new_level_pct"] - rows[0]["change_pp"]
    changes = {datetime.fromisoformat(r["decision_date"]).date(): r for r in rows}

    daily: list[tuple[date, float]] = []
    d = start
    while d <= end:
        if d in changes:
            level = changes[d]["new_level_pct"]
        daily.append((d, level))
        d += timedelta(days=1)

    by_month: dict[str, list[float]] = {}
    for d, lv in daily:
        by_month.setdefault(d.strftime("%Y-%m"), []).append(lv)

    monthly_rows = []
    for month in sorted(by_month):
        vals = by_month[month]
        monthly_rows.append({
            "month": month,
            "opr_month_end": vals[-1],
            "opr_month_mean": round(sum(vals) / len(vals), 3),
            "opr_changed_in_month": 1 if any(
                d.strftime("%Y-%m") == month for d in changes) else 0,
        })
    mout = ROOT / "data" / "opr_monthly.csv"
    with mout.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["month", "opr_month_end", "opr_month_mean",
                                           "opr_changed_in_month"])
        w.writeheader()
        w.writerows(monthly_rows)
    print(f"wrote {mout.relative_to(ROOT)} ({len(monthly_rows)} months)")

    # ---- self-check against known policy checkpoints -----------------------
    checks = [
        ("2020-05", 2.00), ("2020-07", 1.75), ("2022-05", 2.00),
        ("2023-05", 3.00), ("2025-07", 2.75), ("2026-09", 2.75),
    ]
    lookup = {r["month"]: r["opr_month_end"] for r in monthly_rows}
    print("\nself-check (month-end OPR vs known level):")
    ok = True
    for month, expect in checks:
        got = lookup.get(month)
        flag = "OK " if got == expect else "FAIL"
        ok &= got == expect
        print(f"  {flag} {month}: got {got}  expected {expect}")
    print("\n" + ("all checkpoints pass" if ok else "MISMATCH - do not use until fixed"))


if __name__ == "__main__":
    main()
