#!/usr/bin/env python3
"""
Gate for a rebuilt submission of ML Economic 1.

Checks the things that are objectively checkable: file layout, the panel contract, the lag table,
and whether the reported numbers are in a plausible range. It cannot judge the modelling - see
ACCEPTANCE_CHECKLIST.md sections D to H for that.

Usage:  python handoff/verify_submission.py <path-to-submission>
        python handoff/verify_submission.py            # checks the sibling folder (this repo)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REQUIRED_FILES = ["README.md", "requirements.txt", "app/streamlit_app.py"]
REQUIRED_REPORTS = ["reports/model_comparison.md", "reports/intervals.md"]
REQUIRED_PANEL_COLS = ["month", "ipi_growth_yoy", "cpi_inflation_yoy", "u_rate", "opr",
                       "exports_growth_yoy", "myr_per_usd", "li_leading_diffusion",
                       "ppi_growth_yoy", "ipi_index"]
TARGET = "ipi_growth_yoy"


def check(root: Path) -> tuple[list[str], list[str]]:
    ok: list[str] = []
    bad: list[str] = []

    for rel in REQUIRED_FILES + REQUIRED_REPORTS:
        (ok if (root / rel).exists() else bad).append(f"file: {rel}")

    panel_path = root / "data" / "panel_monthly.csv"
    lag_path = root / "data" / "publication_lag.csv"
    if not panel_path.exists():
        bad.append("data/panel_monthly.csv missing - cannot check the panel")
        return ok, bad
    panel = pd.read_csv(panel_path, dtype={"month": str})

    missing = [c for c in REQUIRED_PANEL_COLS if c not in panel.columns]
    n_series = len([c for c in panel.columns if c != "month"])
    (ok if not missing else bad).append(
        f"panel columns present ({n_series} series + month)"
        + (f" - missing {missing}" if missing else ""))

    dupes = int(panel["month"].duplicated().sum())
    (ok if dupes == 0 else bad).append(f"no duplicate months (found {dupes})")

    idx = panel["month"].str[:4].astype(int) * 12 + panel["month"].str[5:7].astype(int)
    gaps = int((idx.diff().dropna() != 1).sum())
    (ok if gaps == 0 else bad).append(f"monthly series is contiguous (gaps: {gaps})")

    if TARGET in panel.columns:
        n = int(panel[TARGET].notna().sum())
        (ok if n >= 100 else bad).append(f"target has {n} non-null months (need >= 100)")
        sd = float(panel[TARGET].std())
        (ok if 4 <= sd <= 12 else bad).append(
            f"target sd = {sd:.1f} pp - plausible for IPI yoy (expect 5-9); a much smaller sd "
            f"means the wrong column or a smoothed series")

    if lag_path.exists():
        lag = pd.read_csv(lag_path)
        if "lag_months_used" in lag.columns and "column" in lag.columns:
            covered = set(lag["column"])
            uncovered = [c for c in panel.columns if c != "month" and c not in covered]
            (ok if not uncovered else bad).append(
                f"lag table covers the panel" + (f" - uncovered: {uncovered[:6]}" if uncovered else ""))
            lags = pd.to_numeric(lag["lag_months_used"], errors="coerce")
            (ok if lags.notna().all() and lags.between(0, 6).all()
             else bad).append("all lag_months within 0-6")
        else:
            bad.append("publication_lag.csv lacks `column` / `lag_months_used`")
    else:
        bad.append("data/publication_lag.csv missing")

    summary = root / "reports" / "backtest_summary.csv"
    if summary.exists():
        s = pd.read_csv(summary)
        mase_cols = [c for c in s.columns if c.endswith("_MASE")]
        if mase_cols:
            lo, hi = float(s[mase_cols].min().min()), float(s[mase_cols].max().max())
            (ok if 0.15 <= lo and hi <= 3.0 else bad).append(
                f"reported MASE range {lo:.3f} to {hi:.3f} - outside 0.15-3.0 is almost always "
                f"a leakage artefact (too good) or a broken origin split (too bad)")
    else:
        bad.append("reports/backtest_summary.csv missing - no reported results to check")

    return ok, bad


def main() -> None:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    print(f"checking: {root}\n")
    ok, bad = check(root)
    for line in ok:
        print(f"  PASS  {line}")
    for line in bad:
        print(f"  FAIL  {line}")
    print(f"\n{len(ok)} passed, {len(bad)} failed")
    if bad:
        print("\nThis submission does not satisfy the objective gate. Fix the failures above; the")
        print("subjective parts (validation protocol, honesty) are in ACCEPTANCE_CHECKLIST.md.")
        raise SystemExit(1)
    print("\nObjective gate passed. Now audit sections D-H of ACCEPTANCE_CHECKLIST.md by hand.")


if __name__ == "__main__":
    main()
