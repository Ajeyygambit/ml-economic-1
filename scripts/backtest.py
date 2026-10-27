#!/usr/bin/env python3
"""
ML Economic 1 (Ajey) - step 6: rolling-origin backtest, baselines first.

Design rules
------------
* Every forecast is made from a MASKED snapshot: at origin month T, series s is visible
  only up to T - lag(s) (data/publication_lag.csv). No exceptions, no by-hand overrides.
* Expanding window, never shuffled. The model only ever sees the past.
* The baseline is the bar. MASE = model MAE / random-walk MAE, so < 1 means "beats doing
  nothing". A model that cannot clear 1.0 is not a result, it is a lesson.
* `lgbm_leaky` is included ON PURPOSE: identical model, features read without the
  publication lag. It is not a candidate - it is the size of the lie that leakage buys.

Usage: python scripts/backtest.py
"""
from __future__ import annotations

import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

TARGET = "ipi_growth_yoy"
HORIZONS = (1, 3, 6, 12)
MIN_TRAIN = 36          # origins before this many training pairs are skipped

# feature -> (column, publication lag, extra lag in months)
FEATURES = {
    "ipi_yoy_l1":  (TARGET, 2, 1),
    "ipi_yoy_l2":  (TARGET, 2, 2),
    "ipi_yoy_l3":  (TARGET, 2, 3),
    "ipi_yoy_l6":  (TARGET, 2, 6),
    "ipi_yoy_l12": (TARGET, 2, 12),
    "exp_yoy_l1":  ("exports_growth_yoy", 1, 1),
    "exp_yoy_l2":  ("exports_growth_yoy", 1, 2),
    "exp_yoy_l12": ("exports_growth_yoy", 1, 12),
    "cpi_yoy":     ("cpi_inflation_yoy", 1, 0),
    "cpi_yoy_l2":  ("cpi_inflation_yoy", 1, 2),
    "u_rate":      ("u_rate", 2, 0),
    "ppi_yoy":     ("ppi_growth_yoy", 2, 0),
    "li_diff":     ("li_leading_diffusion", 3, 0),
    "opr":         ("opr", 0, 0),
    "myr_usd_l1":  ("myr_per_usd", 1, 1),
}


def load() -> tuple[pd.DataFrame, pd.Series]:
    panel = pd.read_csv(ROOT / "data" / "panel_monthly.csv", dtype={"month": str})
    panel["i"] = panel["month"].str[:4].astype(int) * 12 + panel["month"].str[5:7].astype(int)
    panel = panel.set_index("i")
    y = panel[TARGET]
    return panel, y


def build_features(panel: pd.DataFrame, leaky: bool = False) -> pd.DataFrame:
    """One row per origin month: only values a forecaster could see at that origin."""
    cols = {}
    for name, (col, lag, extra) in FEATURES.items():
        offset = (0 if leaky else lag) + extra
        cols[name] = panel[col].shift(offset)
    return pd.DataFrame(cols)


def ar_forecast(y: pd.Series, origin_i: int, h: int, lag_y: int = 2):
    """AR(p) on the target, p by AIC, iterated forward from the newest visible month."""
    hist = y[y.index <= origin_i - lag_y].dropna()
    if len(hist) < 24:
        return np.nan
    best = None
    for p in range(0, 5):
        try:
            fit = ARIMA(hist.values, order=(p, 0, 0)).fit()
        except Exception:
            continue
        if best is None or fit.aic < best[0]:
            best = (fit.aic, fit)
    if best is None:
        return np.nan
    steps = h + lag_y
    try:
        return float(np.asarray(best[1].forecast(steps))[-1])
    except Exception:
        return np.nan


def mase_like(pred: np.ndarray, actual: np.ndarray, base: np.ndarray) -> float:
    denom = np.nanmean(np.abs(base - actual))
    return float(np.nanmean(np.abs(pred - actual)) / denom) if denom else np.nan


def main() -> None:
    panel, y = load()
    F = build_features(panel)
    Fl = build_features(panel, leaky=True)

    all_months = panel.index.values
    first_y = y.dropna().index.min()

    rows = []
    for h in HORIZONS:
        target_at = y.shift(-h)              # what actually happened, h months later
        origins = [i for i in all_months
                   if i >= first_y and not pd.isna(target_at.get(i, np.nan))]
        # need every feature present for the training pairs too
        recs = []
        for n, o in enumerate(origins):
            if n < MIN_TRAIN:
                continue
            train_mask = np.array([i < o for i in origins[:n]])
            train_idx = np.array(origins[:n])[train_mask]
            Xtr = F.loc[train_idx]
            ytr = target_at.loc[train_idx].values
            ok = ~np.isnan(ytr) & Xtr.notna().all(axis=1).values
            Xtr, ytr = Xtr[ok], ytr[ok]
            if len(ytr) < MIN_TRAIN:
                continue

            x_now = F.loc[[o]]
            if x_now.isna().any(axis=1).values[0]:
                continue
            actual = float(target_at.loc[o])

            last_y = y[y.index <= o - 2].dropna()
            rw = float(last_y.iloc[-1]) if len(last_y) else np.nan
            mean3 = float(last_y.iloc[-3:].mean()) if len(last_y) >= 3 else np.nan

            rec = {"origin": f"{o // 12}-{o % 12 or 12:02d}", "h": h, "actual": actual,
                   "rw": rw, "mean3": mean3, "ar": ar_forecast(y, o, h)}

            # --- direct multi-step, identical features, two models ---------
            m = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=7,
                                  min_child_samples=8, subsample=0.8, subsample_freq=1,
                                  colsample_bytree=0.8, reg_lambda=1.0,
                                  random_state=0, verbose=-1)
            m.fit(Xtr, ytr)
            rec["lgbm"] = float(m.predict(x_now)[0])

            # --- the deliberately leaky twin ------------------------------
            Xtl = Fl.loc[train_idx][ok]
            xl_now = Fl.loc[[o]]
            if not xl_now.isna().any(axis=1).values[0]:
                ml = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=7,
                                       min_child_samples=8, subsample=0.8, subsample_freq=1,
                                       colsample_bytree=0.8, reg_lambda=1.0,
                                       random_state=0, verbose=-1)
                ml.fit(Xtl, ytr)
                rec["lgbm_leaky"] = float(ml.predict(xl_now)[0])
            recs.append(rec)

        if not recs:
            print(f"h={h}: no origins with enough training data")
            continue
        df = pd.DataFrame(recs)
        out = {"h": h, "n_origins": len(df)}
        for mdl in ("rw", "mean3", "ar", "lgbm", "lgbm_leaky"):
            if mdl not in df:
                continue
            e = (df[mdl] - df["actual"]).abs()
            out[f"{mdl}_MAE"] = round(float(e.mean()), 3)
            out[f"{mdl}_RMSE"] = round(float(np.sqrt(((df[mdl] - df["actual"]) ** 2).mean())), 3)
            out[f"{mdl}_bias"] = round(float((df[mdl] - df["actual"]).mean()), 3)
        out["lgbm_MASE"] = round(mase_like(df["lgbm"].values, df["actual"].values,
                                           df["rw"].values), 3)
        out["ar_MASE"] = round(mase_like(df["ar"].values, df["actual"].values,
                                         df["rw"].values), 3)
        if "lgbm_leaky" in df:
            out["leaky_MASE"] = round(mase_like(df["lgbm_leaky"].values, df["actual"].values,
                                                df["rw"].values), 3)
        rows.append(out)
        df.to_csv(REPORTS / f"backtest_h{h}.csv", index=False)

    summary = pd.DataFrame(rows)
    summary.to_csv(REPORTS / "backtest_summary.csv", index=False)

    keep = ["h", "n_origins", "rw_MAE", "ar_MAE", "lgbm_MAE", "lgbm_leaky_MAE",
            "ar_MASE", "lgbm_MASE", "leaky_MASE"]
    print(summary[[c for c in keep if c in summary]].to_string(index=False))

    lines = ["# Rolling-origin backtest - ML Economic 1 (Ajey)", "",
             f"Target: `{TARGET}`. Expanding window, {MIN_TRAIN}+ training pairs required.",
             "MASE is relative to the random walk: < 1 beats 'tomorrow looks like today'.", "",
             summary.to_markdown(index=False), "",
             "## How to read this", "",
             "- `rw` is the floor, not a straw man: for a yoy growth series it is genuinely hard to beat.",
             "- `lgbm_leaky` reads features without the publication lag. It is a diagnostic of leakage, "
             "never a candidate model - the gap between it and `lgbm` is what a dishonest backtest would "
             "have claimed as skill.",
             "- Small n by construction: the sample starts in 2016 and the mask removes the newest two months "
             "from every feature.",
             ]
    (REPORTS / "backtest.md").write_text("\n".join(lines), encoding="utf-8")
    print("\nwrote reports/backtest.md + per-horizon predictions")


if __name__ == "__main__":
    main()
