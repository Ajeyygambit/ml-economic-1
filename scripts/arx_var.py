#!/usr/bin/env python3
"""
ML Economic 1 (Ajey) - step 10: AR-X and VAR, the econometric challengers.

The AR(AIC) beat LightGBM under honest selection. Before concluding "econometrics wins",
it has to be asked whether a *multivariate* econometric model wins by more:

  ARX  - direct multi-step ARDL: y(t+h) on AR lags of y plus lagged exports growth, CPI and OPR.
         Direct (not iterated) because iterating would need future values of the exogenous
         variables, which do not exist at the forecast origin - a classic way to leak.
  VAR  - bivariate/multivariate VAR(2) on (y, export growth, OPR), iterated forward.
         The ragged edge is handled explicitly: because each variable is published with a
         different lag, the VAR is estimated on the joint window that ends at the OLDEST
         variable's last available month, then iterated far enough to reach the target month.

Usage: python scripts/arx_var.py
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.api import VAR

from mlcore import (HORIZONS, MIN_TRAIN, REPORTS, ar_forecast, dm_test, load_panel, mase)

warnings.filterwarnings("ignore")

# publication lags, same table as data/publication_lag.csv
LAGS = {"ipi_growth_yoy": 2, "exports_growth_yoy": 1, "cpi_inflation_yoy": 1, "opr": 0}
VAR_VARS = ["ipi_growth_yoy", "exports_growth_yoy", "opr"]


def arx_forecast(panel: pd.DataFrame, origin: int, h: int) -> float:
    """Direct multi-step ARDL, features visible at the origin."""
    y = panel["ipi_growth_yoy"]
    feats = {
        "y_l1": y.shift(LAGS["ipi_growth_yoy"] + 1),
        "y_l2": y.shift(LAGS["ipi_growth_yoy"] + 2),
        "y_l3": y.shift(LAGS["ipi_growth_yoy"] + 3),
        "exp_l1": panel["exports_growth_yoy"].shift(LAGS["exports_growth_yoy"] + 1),
        "exp_l2": panel["exports_growth_yoy"].shift(LAGS["exports_growth_yoy"] + 2),
        "cpi_l1": panel["cpi_inflation_yoy"].shift(LAGS["cpi_inflation_yoy"] + 1),
        "opr": panel["opr"],
    }
    X = pd.DataFrame(feats)
    tgt = y.shift(-h)
    train = X.loc[X.index <= origin].copy()
    train["__y"] = tgt.reindex(train.index)
    train = train.dropna()
    if len(train) < MIN_TRAIN:
        return np.nan
    model = sm.OLS(train["__y"], sm.add_constant(train.drop(columns="__y"))).fit()
    x_now = X.loc[[origin]]
    if x_now.isna().any(axis=1).values[0]:
        return np.nan
    pred = model.predict(sm.add_constant(x_now, has_constant="add"))
    return float(np.asarray(pred)[0])


def var_forecast(panel: pd.DataFrame, origin: int, h: int, maxlags: int = 2) -> float:
    """VAR on the joint window ending at the oldest variable's last visible month."""
    ends = {c: origin - LAGS[c] for c in VAR_VARS}
    joint_end = min(ends.values())
    data = panel[VAR_VARS].loc[panel.index <= joint_end].dropna()
    if len(data) < MIN_TRAIN + 8:
        return np.nan
    try:
        res = VAR(data).fit(maxlags)
    except Exception:
        return np.nan
    # Stability guard. statsmodels' convention: the process is stable when every companion
    # root lies OUTSIDE the unit circle (|root| > 1). Without this check a handful of origins
    # produce exploding iterates (-674pp, -4974pp) that destroy the mean error while the
    # median forecast stays sane. An unstable fit is not a forecast, so do not issue one.
    try:
        if np.min(np.abs(np.asarray(res.roots))) <= 1.0:
            return np.nan
    except Exception:
        return np.nan
    steps = h + (origin - joint_end)          # bridge the ragged edge, then reach the target
    if steps <= 0:
        return np.nan
    try:
        fc = res.forecast(data.values[-res.k_ar:], steps=steps)
        return float(fc[-1, 0])
    except Exception:
        return np.nan


def main() -> None:
    panel, y = load_panel()
    rows = []

    for h in HORIZONS:
        tgt = y.shift(-h)
        origins = [i for i in panel.index
                   if i >= y.dropna().index.min() and not pd.isna(tgt.get(i, np.nan))]
        recs = []
        for n, o in enumerate(origins):
            if n < MIN_TRAIN:
                continue
            last = y[y.index <= o - LAGS["ipi_growth_yoy"]].dropna()
            recs.append({
                "origin": f"{o // 12}-{o % 12 or 12:02d}",
                "actual": float(tgt.loc[o]),
                "rw": float(last.iloc[-1]),
                "ar": ar_forecast(y, o, h),
                "arx": arx_forecast(panel, o, h),
                "var": var_forecast(panel, o, h),
            })
        df = pd.DataFrame(recs)
        df.to_csv(REPORTS / f"arx_var_h{h}.csv", index=False)

        row = {"h": h, "n_origins": len(df)}
        for m in ("ar", "arx", "var"):
            row[f"{m}_MASE"] = round(mase(df[m].values, df["actual"].values, df["rw"].values), 3)
            row[f"{m}_MAE"] = round(float(np.nanmean(np.abs(df[m] - df["actual"]))), 3)
        row["var_origins_stable"] = int(df["var"].notna().sum())
        row["var_origins_skipped_unstable"] = int(df["var"].isna().sum())
        for m in ("arx", "var"):
            ok = df[m].notna()
            st, p = dm_test(np.abs(df.loc[ok, m] - df.loc[ok, "actual"]).values,
                            np.abs(df.loc[ok, "ar"] - df.loc[ok, "actual"]).values, h)
            row[f"{m}_vs_ar_DM"] = round(st, 2)
            row[f"{m}_vs_ar_p"] = round(p, 3)
        rows.append(row)
        print(row)

    out = pd.DataFrame(rows)
    out.to_csv(REPORTS / "arx_var_summary.csv", index=False)

    lines = ["# AR-X and VAR against AR(AIC)", "",
             "Direct multi-step ARDL (`arx`) and an iterated VAR(2) (`var`) on the same masked",
             "snapshots as every other model. MASE relative to the random walk; DM vs AR(AIC).", "",
             out.to_markdown(index=False), "",
             "## Notes", "",
             "- `arx` is estimated directly for each horizon: iterating an ARDL would require",
             "  future exports, CPI and OPR, which is leakage dressed up as a model.",
             "- `var` estimates on the joint window that ends at the oldest variable's last visible",
             "  month (IPI, 2-month lag) and then iterates across the ragged edge.",
             "- A VAR that does not beat the AR does not mean VAR is useless - it means three variables",
             "  and 140 observations are not enough to estimate the extra structure without paying for it.",
             ]
    (REPORTS / "arx_var.md").write_text("\n".join(lines), encoding="utf-8")
    print("\nwrote reports/arx_var.md")


if __name__ == "__main__":
    main()
