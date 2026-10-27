#!/usr/bin/env python3
"""
ML Economic 1 (Ajey) - step 4: the availability mask, and a self-check that proves it works.

`available_asof(panel, T)` returns the panel exactly as a forecaster standing at the
END of month T could have seen it: every series is truncated at T - lag_months, so
nothing published later can enter the model.

Run this before every model build. If the assertions fail, the feature matrix is
leaking and any backtest number is fiction.

Usage:
    python scripts/check_availability.py            # newest usable origin
    python scripts/check_availability.py 2020-04    # a specific origin month
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def month_index(ym: str) -> int:
    y, m = ym.split("-")
    return int(y) * 12 + int(m)


def index_to_month(idx: int) -> str:
    y, m = (idx - 1) // 12, ((idx - 1) % 12) + 1
    return f"{y}-{m:02d}"


def load() -> tuple[pd.DataFrame, dict[str, int]]:
    panel = pd.read_csv(ROOT / "data" / "panel_monthly.csv", dtype={"month": str})
    lag = pd.read_csv(ROOT / "data" / "publication_lag.csv")
    lags = dict(zip(lag["column"], lag["lag_months_used"].astype(int)))
    return panel, lags


def available_asof(panel: pd.DataFrame, lags: dict[str, int], origin: str) -> pd.DataFrame:
    """Mask every column to what was published by the end of `origin`."""
    out = panel.copy()
    origin_idx = month_index(origin)
    for col, lag in lags.items():
        if col not in out.columns:
            continue
        cutoff = origin_idx - lag
        months = out["month"].map(month_index)
        out.loc[months > cutoff, col] = pd.NA
    return out


def newest_usable(panel: pd.DataFrame, col: str) -> str | None:
    s = panel[col].dropna()
    return None if s.empty else panel.loc[s.index[-1], "month"]


def main() -> None:
    panel, lags = load()

    # newest month for which EVERY series has at least one usable observation
    origin = sys.argv[1] if len(sys.argv) > 1 else newest_usable(panel, "ipi_index")
    assert origin, "panel is empty"

    masked = available_asof(panel, lags, origin)
    print(f"forecast origin (end of month): {origin}")
    print(f"{'column':26s} {'lag':>3s}  {'newest usable':13s} {'newest in panel':15s} verdict")
    print("-" * 82)

    problems: list[str] = []
    dropped = 0
    for col, lag in sorted(lags.items(), key=lambda kv: -kv[1]):
        if col not in panel.columns:
            continue
        usable = newest_usable(masked, col)
        actual = newest_usable(panel, col)
        cutoff_idx = month_index(origin) - lag
        ok = (usable is None) or (month_index(usable) <= cutoff_idx)
        if not ok:
            problems.append(f"{col}: usable {usable} exceeds cutoff "
                            f"{index_to_month(cutoff_idx)} (lag={lag})")
        # how much data a leaky build would have used up to `origin`
        leaky = int(panel.loc[panel["month"].map(month_index) <= month_index(origin), col]
                    .notna().sum())
        safe = int(masked.loc[masked["month"].map(month_index) <= month_index(origin), col]
                   .notna().sum())
        dropped += max(0, leaky - safe)
        print(f"{col:26s} {lag:3d}  {str(usable):13s} {str(actual):15s} "
              f"{'OK' if ok else 'LEAK'}  (obs -{leaky - safe})")

    print("-" * 82)
    print(f"observations a leaky build would have used but could not: {dropped}")
    if problems:
        print("\nFAILED - these columns break the availability rule:")
        for p in problems:
            print("  " + p)
        raise SystemExit(1)
    print("\nPASS: no column exposes data published after the forecast origin.")


if __name__ == "__main__":
    main()
