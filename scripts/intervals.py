#!/usr/bin/env python3
"""
ML Economic 1 (Ajey) - step 9: probabilistic forecasts and a calibration audit.

Point forecasts at h=3-6 could not be separated from AR, so the deliverable that still has
value is a calibrated interval. This script asks one question of every interval method:

    does an 80% interval actually contain the outcome 80% of the time?

Methods compared, all on the same masked snapshots and the same rolling origins:
  1. `ar_normal`      - AR(AIC) point with its own normal-theory interval (statsmodels)
  2. `lgbm_quantile`  - LightGBM trained directly on the 5th/10th/50th/90th/95th percentiles
  3. `lgbm_conformal` - LightGBM point +/- the empirical quantile of PAST residuals only
  4. `ar_conformal`   - AR point +/- the empirical quantile of PAST residuals only

The conformal variants are the honest operational approach: they never look at a future
outcome to size the interval, only at how wrong the model has already been.

Usage: python scripts/intervals.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mlcore import (CONFIGS, HORIZONS, MIN_TRAIN, REPORTS, ar_forecast, build_features, lgbm,
                    load_panel, mase, origins_for, pinball, training_set)

QUANTILES = (0.025, 0.10, 0.50, 0.90, 0.975)
MIN_PAST_ERRORS = 12
QUANT_OVER = dict(n_estimators=200)      # keep the quantile fits tractable


def main() -> None:
    panel, y = load_panel()
    F = build_features(panel)
    summary = []

    for h in HORIZONS:
        origins = origins_for(y, panel, h)
        recs = []
        for n, o in enumerate(origins):
            if n < MIN_TRAIN:
                continue
            X, t = training_set(F, y, h, origins, o)
            if X is None or len(t) < MIN_TRAIN:
                continue
            x_now = F.loc[[o]]
            if x_now.isna().any(axis=1).values[0]:
                continue

            rec = {"i": o, "origin": f"{o // 12}-{o % 12 or 12:02d}",
                   "actual": float(y.shift(-h).loc[o]),
                   "rw": float(y[y.index <= o - 2].dropna().iloc[-1])}

            ar_pt, ar_80, ar_95 = ar_forecast(y, o, h, return_conf=True)
            rec.update({"ar": ar_pt, "ar80_lo": ar_80[0], "ar80_hi": ar_80[1],
                        "ar95_lo": ar_95[0], "ar95_hi": ar_95[1]})

            m = lgbm(CONFIGS["heavy"], X, t)
            rec["lgbm"] = float(m.predict(x_now)[0])

            qp = {}
            for a in QUANTILES:
                qm = lgbm(CONFIGS["heavy"], X, t, objective="quantile", alpha=a, **QUANT_OVER)
                qp[a] = float(qm.predict(x_now)[0])
            rec.update({f"q{int(a * 1000):03d}": v for a, v in qp.items()})
            recs.append(rec)

        df = pd.DataFrame(recs).reset_index(drop=True)

        # ---- conformal: interval half-width from PAST errors only -----------
        for model in ("lgbm", "ar"):
            err = (df[model] - df["actual"]).abs()
            for nom in (0.80, 0.95):
                lo_col, hi_col = f"{model}_c{int(nom * 100)}_lo", f"{model}_c{int(nom * 100)}_hi"
                lo, hi = [], []
                for i in range(len(df)):
                    past = err.iloc[:i].dropna()
                    if len(past) < MIN_PAST_ERRORS:
                        lo.append(np.nan); hi.append(np.nan); continue
                    q = np.quantile(past, nom)
                    lo.append(df[model].iloc[i] - q)
                    hi.append(df[model].iloc[i] + q)
                df[lo_col], df[hi_col] = lo, hi

        n_ok = int(df["ar_c80_lo"].notna().sum())
        res = {"h": h, "n_origins": len(df), "n_scored_after_warmup": n_ok,
               "point_MASE_ar": round(mase(df["ar"].values, df["actual"].values, df["rw"].values), 3),
               "point_MASE_lgbm": round(mase(df["lgbm"].values, df["actual"].values,
                                             df["rw"].values), 3)}
        for label, lo, hi in (
            ("ar_normal_80", df["ar80_lo"], df["ar80_hi"]),
            ("ar_normal_95", df["ar95_lo"], df["ar95_hi"]),
            ("lgbm_quantile_80", df["q100"], df["q900"]),
            ("lgbm_quantile_95", df["q025"], df["q975"]),
            ("lgbm_conformal_80", df["lgbm_c80_lo"], df["lgbm_c80_hi"]),
            ("lgbm_conformal_95", df["lgbm_c95_lo"], df["lgbm_c95_hi"]),
            ("ar_conformal_80", df["ar_c80_lo"], df["ar_c80_hi"]),
            ("ar_conformal_95", df["ar_c95_lo"], df["ar_c95_hi"]),
        ):
            m_ok = lo.notna() & hi.notna()
            if m_ok.sum() < 5:
                continue
            a = df.loc[m_ok, "actual"].values
            l, u = lo[m_ok].values, hi[m_ok].values
            nom = 0.80 if label.endswith("80") else 0.95
            res[f"{label}_coverage"] = round(float(np.mean((a >= l) & (a <= u))), 3)
            res[f"{label}_width"] = round(float(np.mean(u - l)), 2)
            res[f"{label}_pinball"] = round(pinball(a, l, u, 1 - nom), 3)

        summary.append(res)
        df.to_csv(REPORTS / f"intervals_h{h}.csv", index=False)

    out = pd.DataFrame(summary)
    out.to_csv(REPORTS / "intervals_summary.csv", index=False)
    print(out.to_string(index=False))

    # ---- write the report ------------------------------------------------
    lines = ["# Probabilistic forecasts - calibration audit", "",
             "Target `ipi_growth_yoy`, rolling origins, publication-lag mask enforced.",
             "Nominal coverage is what the interval promises; empirical is what it delivered.", ""]
    for h in HORIZONS:
        r = out[out["h"] == h]
        if r.empty:
            continue
        r = r.iloc[0]
        lines += [f"## h = {h} (n = {r['n_origins']} origins, {r['n_scored_after_warmup']} after the conformal warm-up)", "",
                  f"Point MASE - AR {r['point_MASE_ar']}, LightGBM {r['point_MASE_lgbm']}.", ""]
        rows = []
        for label, nom in (("ar_normal_80", 0.80), ("lgbm_quantile_80", 0.80),
                           ("lgbm_conformal_80", 0.80), ("ar_conformal_80", 0.80),
                           ("ar_normal_95", 0.95), ("lgbm_quantile_95", 0.95),
                           ("lgbm_conformal_95", 0.95), ("ar_conformal_95", 0.95)):
            key = f"{label}_coverage"
            if key not in r or pd.isna(r[key]):
                continue
            rows.append({"method": label, "nominal": nom, "empirical": r[key],
                         "gap": round(r[key] - nom, 3),
                         "mean width (pp)": r.get(f"{label}_width"),
                         "pinball": r.get(f"{label}_pinball")})
        lines += [pd.DataFrame(rows).to_markdown(index=False), ""]
    lines += ["## How to read this", "",
              "- A method is calibrated when empirical coverage lands near nominal. Over-coverage "
              "means the interval is too wide to be useful; under-coverage means it lies.",
              "- Pinball loss rewards sharpness subject to calibration, so it is the tie-breaker "
              "between two methods that are both roughly calibrated.",
              "- Conformal intervals warm up: the first 12 origins have no interval because there "
              "was no error history to size them from. That is a feature, not a gap.",
              ]
    (REPORTS / "intervals.md").write_text("\n".join(lines), encoding="utf-8")
    print("\nwrote reports/intervals.md + intervals_summary.csv")


if __name__ == "__main__":
    main()
