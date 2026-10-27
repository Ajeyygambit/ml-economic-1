#!/usr/bin/env python3
"""
ML Economic 1 (Ajey) - step 3: build the publication-lag (availability) mask.

THE RULE THIS ENFORCES
----------------------
A forecast made at the end of month T may only use values that had already been
*released* by then. Malaysia's statistics are released with a lag, and the lag
differs by series (CPI ~3 weeks, IPI ~2 months, M2 ~4 months). Ignore that and the
model looks brilliant in backtest and is worthless live - classic leakage.

So every series gets `lag_months`: at the end of month T the newest usable
observation is month T - lag_months.

HOW THE LAG IS ESTABLISHED
--------------------------
Primary evidence = what the official API actually holds today. If today is
2026-10 and the CPI catalogue stops at 2026-09, then CPI is available at T-1.
That is an *observed upper bound* on the lag (it can only be too small if a
release slipped), which is the safe direction for backtesting.

Output: data/publication_lag.csv   (machine-readable, consumed by the feature builder)

Usage:  python scripts/build_publication_lag.py
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TODAY = date.today()
T_YEAR, T_MONTH = TODAY.year, TODAY.month

# Documented release practice (DOSM/BNM), used to sanity-check the observed lag.
DOCUMENTED = {
    "cpi_inflation_yoy": ("DOSM CPI release ~3-4 weeks after month end", 1),
    "cpi_inflation_mom": ("DOSM CPI release ~3-4 weeks after month end", 1),
    "cpi_div01_yoy": ("DOSM CPI release ~3-4 weeks after month end", 1),
    "cpi_div04_yoy": ("DOSM CPI release ~3-4 weeks after month end", 1),
    "cpi_core_yoy": ("DOSM CPI release ~3-4 weeks after month end", 1),
    "exports_rm_mil": ("DOSM trade release ~4-5 weeks after month end", 1),
    "imports_rm_mil": ("DOSM trade release ~4-5 weeks after month end", 1),
    "trade_balance_rm_mil": ("DOSM trade release ~4-5 weeks after month end", 1),
    "exports_growth_yoy": ("DOSM trade release ~4-5 weeks after month end", 1),
    "imports_growth_yoy": ("DOSM trade release ~4-5 weeks after month end", 1),
    "ipi_index": ("DOSM IPI release ~2 months after reference month", 2),
    "ipi_index_sa": ("DOSM IPI release ~2 months after reference month", 2),
    "ipi_growth_mom": ("DOSM IPI release ~2 months after reference month", 2),
    "ipi_growth_yoy": ("DOSM IPI release ~2 months after reference month", 2),
    "ipi_mining_index": ("DOSM IPI release ~2 months after reference month", 2),
    "ipi_manufacturing_index": ("DOSM IPI release ~2 months after reference month", 2),
    "ipi_electricity_index": ("DOSM IPI release ~2 months after reference month", 2),
    "ppi_growth_yoy": ("DOSM PPI release ~2 months after reference month", 2),
    "u_rate": ("DOSM LFS monthly release ~5-6 weeks after month end", 2),
    "p_rate": ("DOSM LFS monthly release ~5-6 weeks after month end", 2),
    "lf_employed": ("DOSM LFS monthly release ~5-6 weeks after month end", 2),
    "li_leading": ("DOSM Malaysian Economic Indicators, ~2-3 months", 3),
    "li_coincident": ("DOSM Malaysian Economic Indicators, ~2-3 months", 3),
    "li_lagging": ("DOSM Malaysian Economic Indicators, ~2-3 months", 3),
    "li_leading_diffusion": ("DOSM Malaysian Economic Indicators, ~2-3 months", 3),
    "blr": ("BNM monthly interest-rate statistics, ~3-4 months", 4),
    "fdr_1mo": ("BNM monthly interest-rate statistics, ~3-4 months", 4),
    "fdr_3mo": ("BNM monthly interest-rate statistics, ~3-4 months", 4),
    "m2_rm_mil": ("BNM monetary aggregates, ~3-4 months", 4),
    "m3_rm_mil": ("BNM monetary aggregates, ~3-4 months", 4),
    "opr": ("MPC decision published 3pm on decision day - available immediately", 0),
    "opr_changed_in_month": ("MPC decision published 3pm on decision day", 0),
    "myr_per_usd": ("BNM daily noon rate; monthly mean only complete at month end", 0),
}


def month_index(ym: str) -> int:
    y, m = ym.split("-")
    return int(y) * 12 + int(m)


def main() -> None:
    panel = pd.read_csv(ROOT / "data" / "panel_monthly.csv")
    now = T_YEAR * 12 + T_MONTH
    rows = []
    for col in panel.columns:
        if col in ("month",):
            continue
        s = panel[col].dropna()
        if s.empty:
            continue
        last = panel.loc[s.index[-1], "month"]
        observed = now - month_index(last)          # months behind current month
        note, documented = DOCUMENTED.get(col, ("(undocumented series!)", None))
        mask = observed if documented is None else max(observed, documented)
        rows.append({
            "column": col,
            "newest_obs": last,
            "months_behind_today": observed,
            "documented_release_lag": documented if documented is not None else "",
            "release_practice": note,
            "lag_months_used": mask,
            "flag": ("OK" if documented is not None and observed <= documented + 1
                     else "REVIEW"),
        })

    out = ROOT / "data" / "publication_lag.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out.relative_to(ROOT)}  ({len(rows)} series)")
    print(f"reference month T = {T_YEAR}-{T_MONTH:02d}\n")
    for r in sorted(rows, key=lambda r: (-r["lag_months_used"], r["column"])):
        print(f"  lag={r['lag_months_used']}  {r['column']:24s} newest={r['newest_obs']}  "
              f"({r['months_behind_today']} mo behind)  {r['flag']}")
    review = [r["column"] for r in rows if r["flag"] == "REVIEW"]
    print("\n" + (f"REVIEW NEEDED: {review}" if review
                  else "all series consistent with documented release practice"))


if __name__ == "__main__":
    main()
