#!/usr/bin/env python3
"""
ML Economic 1 (Ajey) - step 7: does the ML model lose because it is weak, or because I tuned it badly?

A backtest that shows LightGBM losing to AR(1) is worthless if the hyperparameters were
never touched - the first question any reviewer asks. So: same features, same masked
snapshots, same rolling origins, four configurations, report all of them.

This is a robustness check on the honest result, not a hunt for the best number.
Configurations are fixed a priori (default / regularised / heavily regularised / linear
leaves); none is selected by looking at the out-of-sample scores across all horizons.

Usage: python scripts/tune_lgbm.py
"""
from __future__ import annotations

import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    "default": dict(n_estimators=300, learning_rate=0.05, num_leaves=7, min_child_samples=8,
                    subsample=0.8, colsample_bytree=0.8),
    "regularised": dict(n_estimators=150, learning_rate=0.03, num_leaves=3,
                        min_child_samples=15, subsample=0.8, colsample_bytree=0.6),
    "heavy": dict(n_estimators=400, learning_rate=0.02, num_leaves=4, min_child_samples=20,
                  subsample=0.7, colsample_bytree=0.5, reg_lambda=5.0),
    "linear_leaves": dict(n_estimators=100, learning_rate=0.05, num_leaves=3,
                          min_child_samples=12, linear_tree=True),
}
MIN_TRAIN = 36


def main() -> None:
    panel = pd.read_csv(ROOT / "data" / "panel_monthly.csv", dtype={"month": str})
    panel["i"] = panel["month"].str[:4].astype(int) * 12 + panel["month"].str[5:7].astype(int)
    panel = panel.set_index("i")
    y = panel["ipi_growth_yoy"]

    # identical masked feature set to scripts/backtest.py
    F = pd.DataFrame({
        "ipi_yoy_l1": y.shift(3), "ipi_yoy_l2": y.shift(4), "ipi_yoy_l3": y.shift(5),
        "ipi_yoy_l6": y.shift(8), "ipi_yoy_l12": y.shift(14),
        "exp_yoy_l1": panel["exports_growth_yoy"].shift(2),
        "exp_yoy_l2": panel["exports_growth_yoy"].shift(3),
        "exp_yoy_l12": panel["exports_growth_yoy"].shift(13),
        "cpi_yoy": panel["cpi_inflation_yoy"].shift(1),
        "cpi_yoy_l2": panel["cpi_inflation_yoy"].shift(3),
        "u_rate": panel["u_rate"].shift(2), "ppi_yoy": panel["ppi_growth_yoy"].shift(2),
        "li_diff": panel["li_leading_diffusion"].shift(3), "opr": panel["opr"],
        "myr_usd_l1": panel["myr_per_usd"].shift(2),
    })

    rows = []
    for h in (1, 3, 6, 12):
        tgt = y.shift(-h)
        origins = [i for i in panel.index
                   if i >= y.dropna().index.min() and not pd.isna(tgt.get(i, np.nan))]
        preds = {k: [] for k in MODELS}
        rw, actual, origin_used = [], [], []
        for n, o in enumerate(origins):
            if n < MIN_TRAIN:
                continue
            idx = np.array(origins[:n])
            Xtr, ytr = F.loc[idx], tgt.loc[idx].values
            ok = ~np.isnan(ytr) & Xtr.notna().all(axis=1).values
            if ok.sum() < MIN_TRAIN:
                continue
            x_now = F.loc[[o]]
            if x_now.isna().any(axis=1).values[0]:
                continue
            for name, params in MODELS.items():
                m = lgb.LGBMRegressor(random_state=0, verbose=-1, subsample_freq=1, **params)
                m.fit(Xtr[ok], ytr[ok])
                preds[name].append(float(m.predict(x_now)[0]))
            rw.append(float(y[y.index <= o - 2].dropna().iloc[-1]))
            actual.append(float(tgt.loc[o]))
            origin_used.append(o)

        a = np.array(actual)
        base = np.mean(np.abs(np.array(rw) - a))
        row = {"h": h, "n_origins": len(a), "rw_MASE": 1.0}
        for name, p in preds.items():
            row[f"{name}_MASE"] = round(float(np.mean(np.abs(np.array(p) - a)) / base), 3)
            row[f"{name}_MAE"] = round(float(np.mean(np.abs(np.array(p) - a))), 3)
        rows.append(row)
        # keep per-origin predictions so the differences can be significance-tested
        pd.DataFrame({"origin": [f"{i // 12}-{i % 12 or 12:02d}" for i in origin_used],
                      "actual": actual, "rw": rw, **preds}).to_csv(
            ROOT / "reports" / f"lgbm_sensitivity_h{h}.csv", index=False)
        print(row)

    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "reports" / "lgbm_sensitivity.csv", index=False)
    best = {h: min((r[f"{k}_MASE"], k) for k in MODELS) for h, r in
            zip(df["h"], df.to_dict("records"))}
    print("\nbest configuration per horizon (MASE, model):", best)
    print("AR(1)-AIC MASE for comparison: see reports/backtest_summary.csv")
    print("\nwrote reports/lgbm_sensitivity.csv")


if __name__ == "__main__":
    main()
