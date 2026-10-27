#!/usr/bin/env python3
"""
ML Economic 1 (Ajey) - step 8: nested hyperparameter selection.

The problem this fixes: in the first pass the winning LightGBM configuration was chosen by
looking at the out-of-sample scores, which makes the h=1 result optimistically biased.

The correct procedure, implemented here:
  outer loop  - walk forward through forecast origins, exactly as the honest backtest does
  inner loop  - inside each outer training window only, hold out the most recent 12 training
                pairs, score every configuration on them, keep the winner
  fit & score - refit the winner on the full outer training window, predict the outer origin
                ONCE

Configurations never see the outer test target. The result is the number that can be quoted.

Usage: python scripts/nested_select.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mlcore import (CONFIGS, HORIZONS, MIN_TRAIN, REPORTS, ar_forecast, build_features,
                    dm_test, lgbm, load_panel, mase, origins_for, training_set)

INNER_HOLDOUT = 12


def main() -> None:
    panel, y = load_panel()
    F = build_features(panel)
    rows, picked_log = [], []

    for h in HORIZONS:
        origins = origins_for(y, panel, h)
        nested, oracle_best, default_pred, heavy_pred = [], [], [], []
        ar_pred, actual, rw_pred, chosen, origin_used = [], [], [], [], []

        for n, o in enumerate(origins):
            if n < MIN_TRAIN:
                continue
            X, t = training_set(F, y, h, origins, o)
            if X is None or len(t) < MIN_TRAIN + INNER_HOLDOUT:
                continue
            x_now = F.loc[[o]]
            if x_now.isna().any(axis=1).values[0]:
                continue
            y_now = float(y.shift(-h).loc[o])
            base_now = float(y[y.index <= o - 2].dropna().iloc[-1])

            # ---- inner selection: only the outer training window is used -----
            Xtr, ttr = X.iloc[:-INNER_HOLDOUT], t[:-INNER_HOLDOUT]
            Xva, tva = X.iloc[-INNER_HOLDOUT:], t[-INNER_HOLDOUT:]
            scores = {}
            for name, params in CONFIGS.items():
                m = lgbm(params, Xtr, ttr)
                scores[name] = float(np.mean(np.abs(m.predict(Xva) - tva)))
            best = min(scores, key=scores.get)

            m_best = lgbm(CONFIGS[best], X, t)
            nested.append(float(m_best.predict(x_now)[0]))
            chosen.append(best)

            # reference only: which config would have won at this origin, judged after the fact
            per_cfg = {}
            for name, params in CONFIGS.items():
                m = lgbm(params, X, t)
                per_cfg[name] = abs(float(m.predict(x_now)[0]) - y_now)
                if name == "default":
                    default_pred.append(float(m.predict(x_now)[0]))
                if name == "heavy":
                    heavy_pred.append(float(m.predict(x_now)[0]))
            oracle_best.append(abs(per_cfg[min(per_cfg, key=per_cfg.get)] - y_now))

            ar_pred.append(ar_forecast(y, o, h))
            actual.append(y_now)
            rw_pred.append(base_now)
            origin_used.append(o)

        actual = np.array(actual)
        res = {"h": h, "n_origins": len(actual)}
        for name, pred in (("ar", ar_pred), ("rw", rw_pred), ("lgbm_default", default_pred),
                           ("lgbm_heavy_fixed", heavy_pred), ("lgbm_nested", nested)):
            p = np.array(pred)
            res[f"{name}_MASE"] = round(mase(p, actual, np.array(rw_pred)), 3)
            res[f"{name}_MAE"] = round(float(np.nanmean(np.abs(p - actual))), 3)
        # oracle: post-hoc best config per origin, lower bound on what selection could buy
        res["oracle_MAE"] = round(float(np.mean(oracle_best)), 3)
        st, p = dm_test(np.abs(np.array(nested) - actual), np.abs(np.array(ar_pred) - actual), h)
        res["nested_vs_ar_DM"] = round(st, 2)
        res["nested_vs_ar_p"] = round(p, 3)
        rows.append(res)
        picked_log.append({"h": h, **{k: chosen.count(k) for k in CONFIGS}})

        pd.DataFrame({"origin": [f"{o // 12}-{o % 12 or 12:02d}" for o in origin_used],
                      "actual": actual, "rw": rw_pred, "ar": ar_pred,
                      "lgbm_default": default_pred, "lgbm_heavy": heavy_pred,
                      "lgbm_nested": nested,
                      "config_chosen": chosen}).to_csv(
            REPORTS / f"nested_h{h}.csv", index=False)

    df = pd.DataFrame(rows)
    df.to_csv(REPORTS / "nested_selection.csv", index=False)
    print(df.to_string(index=False))
    print("\nconfiguration chosen by the inner loop, per horizon:")
    print(pd.DataFrame(picked_log).to_string(index=False))


if __name__ == "__main__":
    main()
