#!/usr/bin/env python3
"""
ML Economic 1 (Ajey) - Malaysian Macro data pipeline, step 1: acquire.

Pulls every series we need straight from the official open-data API
(api.data.gov.my, run by DOSM/MAMPU) plus Bank Negara Malaysia for the OPR,
and writes:
    data/raw/<series>.csv      one file per downloaded catalogue (verbatim)
    data/panel_monthly.csv      wide monthly panel, 2015-01 onward
    data/panel_quarterly.csv    wide quarterly panel (GDP)
    data/manifest.json          source URL, fetch time, row counts, coverage

Design rules (do not break these):
  * stdlib only - runs on any Python 3.9+ with no installs.
  * never silently forward-fill across a gap; leave NaN and let the modelling
    layer declare an explicit imputation policy.
  * record the exact URL + fetch timestamp for every series (audit trail).

Usage:  python scripts/fetch_data.py
"""
from __future__ import annotations

import csv
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

API = "https://api.data.gov.my/data-catalogue"
MANIFEST: list[dict] = []

# Monthly start of the modelling sample. Earlier data is still downloaded and
# kept in raw/ (useful for long-run diagnostics), the panel is trimmed later.
PANEL_START = "2015-01-01"


def fetch(catalogue_id: str) -> list[dict]:
    url = f"{API}?id={catalogue_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "ml-economic-1/0.1"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        rows = json.loads(resp.read().decode("utf-8"))
    note_raw(catalogue_id, url, rows)
    return rows


def note_raw(cid: str, url: str, rows: list[dict]) -> None:
    if not rows:
        MANIFEST.append({"series": cid, "url": url, "rows": 0, "status": "EMPTY"})
        return
    path = RAW / f"{cid}.csv"
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    dates = sorted(str(r["date"]) for r in rows if r.get("date"))
    MANIFEST.append({
        "series": cid,
        "url": url,
        "rows": len(rows),
        "columns": cols,
        "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "raw_file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "status": "OK",
    })


def monthly(series: dict[str, dict[str, float]], date: str, **values: float | None) -> None:
    """Accumulate one month of the wide panel."""
    row = series.setdefault(date[:7], {})
    for k, v in values.items():
        if v is not None:
            row[k] = v


def build_panel() -> tuple[list[dict], list[dict]]:
    panel: dict[str, dict] = {}

    # ---- 1. Industrial production (candidate target family) -----------------
    by_date_ipi: dict[str, dict] = {}
    for r in fetch("ipi"):
        by_date_ipi.setdefault(r["date"][:7], {})[r["series"]] = r
    for month, vals in by_date_ipi.items():
        monthly(
            panel, month,
            ipi_index=(vals.get("abs") or {}).get("index"),
            ipi_index_sa=(vals.get("abs") or {}).get("index_sa"),
            ipi_growth_mom=(vals.get("growth_mom") or {}).get("index"),
            ipi_growth_yoy=(vals.get("growth_yoy") or {}).get("index"),
        )

    # ---- 2. IPI by section: B mining, C manufacturing, D electricity --------
    sec: dict[str, dict[str, dict]] = {}
    for r in fetch("ipi_1d"):
        if r["series"] == "abs":
            sec.setdefault(r["date"][:7], {})[r["section"]] = r
    for month, d in sec.items():
        for code, name in (("B", "mining"), ("C", "manufacturing"), ("D", "electricity")):
            if code in d:
                monthly(panel, month, **{f"ipi_{name}_index": d[code].get("index")})

    # ---- 3. Headline CPI inflation, overall + core --------------------------
    cpi = fetch("cpi_headline_inflation")
    cpi_by: dict[str, dict[str, dict]] = {}
    for r in cpi:
        cpi_by.setdefault(r["date"][:7], {})[r["division"]] = r
    for month, d in cpi_by.items():
        if "overall" in d:
            monthly(
                panel, month,
                cpi_inflation_yoy=d["overall"].get("inflation_yoy"),
                cpi_inflation_mom=d["overall"].get("inflation_mom"),
            )
        for div in ("01", "04"):  # food & non-alcoholic beverages, housing/utilities
            if div in d:
                monthly(panel, month, **{f"cpi_div{div}_yoy": d[div].get("inflation_yoy")})

    for r in fetch("cpi_core_inflation"):
        monthly(panel, r["date"][:7], cpi_core_yoy=r.get("inflation_yoy"))

    # ---- 4. Labour market (seasonally adjusted) ----------------------------
    for r in fetch("lfs_month_sa"):
        monthly(
            panel, r["date"][:7],
            u_rate=r.get("u_rate"),
            p_rate=r.get("p_rate"),
            lf_employed=r.get("lf_employed"),
        )

    # ---- 5. External trade (API returns ringgit; converted to RM million) ---
    trade: dict[str, dict[str, dict]] = {}
    for r in fetch("trade_headline"):
        trade.setdefault(r["date"][:7], {})[r["series"]] = r

    def rm_mil(v):
        # source series is in ringgit (verified: 2015-01 exports = 62,971,395,081
        # = RM 62.97b); divide to get the labelled unit
        return None if v is None else round(v / 1_000_000, 3)

    for month, d in trade.items():
        lvl = d.get("abs") or {}
        gro = d.get("growth_yoy") or {}
        monthly(
            panel, month,
            exports_rm_mil=rm_mil(lvl.get("exports")),
            imports_rm_mil=rm_mil(lvl.get("imports")),
            trade_balance_rm_mil=rm_mil(lvl.get("balance")),
            exports_growth_yoy=gro.get("exports"),
            imports_growth_yoy=gro.get("imports"),
        )

    # ---- 6. Exchange rate: daily -> monthly mean (MYR per unit) ------------
    fx: dict[str, list[float]] = {}
    for r in fetch("exchangerates"):
        if r.get("usd") is not None:
            fx.setdefault(r["date"][:7], []).append(r["usd"])
    for month, vals in fx.items():
        monthly(panel, month, myr_per_usd=round(sum(vals) / len(vals), 4))

    # ---- 7. Interest rates (commercial bank weighted rates) ---------------
    rates: dict[str, dict[str, dict]] = {}
    for r in fetch("interestrates"):
        if r.get("bank") == "commercial":
            rates.setdefault(r["date"][:7], {})[r["rate"]] = r
    for month, d in rates.items():
        monthly(
            panel, month,
            blr=(d.get("blr") or {}).get("value"),
            fdr_1mo=(d.get("fdr_1mo") or {}).get("value"),
            fdr_3mo=(d.get("fdr_3mo") or {}).get("value"),
        )

    # ---- 8. Producer prices ------------------------------------------------
    ppi: dict[str, dict[str, dict]] = {}
    for r in fetch("ppi"):
        ppi.setdefault(r["date"][:7], {})[r["series"]] = r
    for month, d in ppi.items():
        monthly(panel, month, ppi_growth_yoy=(d.get("growth_yoy") or {}).get("index"))

    # ---- 9. Monetary aggregates -------------------------------------------
    mon: dict[str, dict[str, dict]] = {}
    for r in fetch("monetary_aggregates"):
        mon.setdefault(r["date"][:7], {})[r["measure"]] = r
    for month, d in mon.items():
        monthly(
            panel, month,
            m2_rm_mil=(d.get("m2_total") or {}).get("value"),
            m3_rm_mil=(d.get("m3_total") or {}).get("value"),
        )

    # ---- 10. DOSM leading / coincident / lagging index ---------------------
    for r in fetch("economic_indicators"):
        monthly(
            panel, r["date"][:7],
            li_leading=r.get("leading"),
            li_coincident=r.get("coincident"),
            li_lagging=r.get("lagging"),
            li_leading_diffusion=r.get("leading_diffusion"),
        )

    # ---- 11. Overnight Policy Rate (from scripts/fetch_opr.py) -------------
    opr_path = ROOT / "data" / "opr_monthly.csv"
    if opr_path.exists():
        with opr_path.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                monthly(panel, r["month"],
                        opr=float(r["opr_month_end"]),
                        opr_changed_in_month=int(r["opr_changed_in_month"]))
        MANIFEST.append({
            "series": "opr",
            "url": "https://www.bnm.gov.my/monetary-stability/opr-decisions/-/tag/opr-YYYY",
            "source": "Bank Negara Malaysia (MPC decisions, walked by year tag)",
            "raw_file": "data/opr_monthly.csv",
            "status": "OK",
        })
    else:
        print("WARNING: data/opr_monthly.csv missing - run scripts/fetch_opr.py first")
        MANIFEST.append({"series": "opr", "status": "MISSING - run fetch_opr.py"})

    monthly_rows = [{"month": m, **panel[m]} for m in sorted(panel)
                    if m >= PANEL_START[:7]]

    # ---- 11. Quarterly GDP (real, seasonally adjusted, RM million) --------
    gq: dict[str, dict] = {}
    for r in fetch("gdp_qtr_real_sa"):
        gq.setdefault(str(r["date"])[:10], {})["gdp_real_sa_rm_mil"] = r["value"]
    for r in fetch("gdp_qtr_real"):
        if r.get("series") == "abs":
            gq.setdefault(str(r["date"])[:10], {})["gdp_real_rm_mil"] = r["value"]
        elif r.get("series") == "growth_yoy":
            gq.setdefault(str(r["date"])[:10], {})["gdp_growth_yoy"] = r["value"]
    quarterly_rows = [{"quarter_start": d, **gq[d]} for d in sorted(gq)]

    return monthly_rows, quarterly_rows


def write_csv(path: Path, rows: list[dict]) -> None:
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in cols})
    print(f"wrote {path.relative_to(ROOT)}  rows={len(rows)}  cols={len(cols)}")


def main() -> None:
    monthly_rows, quarterly_rows = build_panel()
    write_csv(ROOT / "data" / "panel_monthly.csv", monthly_rows)
    write_csv(ROOT / "data" / "panel_quarterly.csv", quarterly_rows)
    (ROOT / "data" / "manifest.json").write_text(
        json.dumps({"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "api": API, "sources": MANIFEST}, indent=2),
        encoding="utf-8")
    print("wrote data/manifest.json")


if __name__ == "__main__":
    main()
