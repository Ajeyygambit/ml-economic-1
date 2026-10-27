#!/usr/bin/env python3
"""
ML Economic 1 (Ajey) - step 11: regime detection on variance, and what it does to the intervals.

The exploratory analysis found no break in the mean dynamics (Chow p=0.85 at 2020-03,
CUSUM p=0.31), so a regime model justified on "the mean relationship changed" would be
contradicted by the evidence. Volatility is a different matter: activity growth is clearly
heteroskedastic (2020, 2021 and 2026 look nothing like 2017).

What this does:
  1. Marks a two-state volatility regime with a Markov-switching AR, fitted EXPANDING - at each
     month only data up to that month is used, so the regime label is available in real time.
  2. Asks whether forecast errors and interval coverage differ across the two regimes.
  3. If coverage collapses in the turbulent state, the fixed-width interval is the problem and
     regime-conditional widths are the fix - tested, not assumed.

Usage: python scripts/regime.py
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

from mlcore import HORIZONS, REPORTS, load_panel

warnings.filterwarnings("ignore")

MIN_FIT = 60          # months required before a regime is labelled
REGIME_FILE = REPORTS / "regime_probabilities.csv"


def fit_regimes(y: pd.Series) -> pd.DataFrame:
    """Expanding-window two-state Markov switching model with state-dependent variance."""
    rows = []
    idx = y.dropna().index
    for n, month in enumerate(idx):
        hist = y.loc[:month].dropna()
        if len(hist) < MIN_FIT:
            continue
        # standardise inside the window: with a raw series the optimiser converges to a
        # degenerate state (variance ~1e5, probability ~0), which makes the regime vacuous.
        # Using the window's own mean/sd keeps the label real-time.
        z = (hist - hist.mean()) / hist.std()
        try:
            mod = MarkovRegression(z.values, k_regimes=2, trend="c", switching_variance=True)
            res = mod.fit(disp=False, maxiter=1000)
        except Exception:
            continue
        # identify the high-variance state by its fitted sigma
        names = list(res.model.param_names)
        try:
            sigmas = [float(res.params[names.index(f"sigma2[{k}]")]) for k in range(2)]
        except Exception:
            continue
        hi = int(np.argmax(sigmas))
        probs = np.asarray(res.filtered_marginal_probabilities)
        rows.append({"i": month, "p_high_vol": float(probs[-1, hi]),
                     "sd_calm": float(np.sqrt(min(sigmas))),
                     "sd_turbulent": float(np.sqrt(max(sigmas)))})
    df = pd.DataFrame(rows)
    df["month"] = [f"{i // 12}-{i % 12 or 12:02d}" for i in df["i"]]
    return df


def main() -> None:
    panel, y = load_panel()
    reg = fit_regimes(y)
    reg.to_csv(REGIME_FILE, index=False)
    print(f"regime series: {len(reg)} months labelled, "
          f"{reg['p_high_vol'].gt(0.5).sum()} in the turbulent state")

    # ---- do errors and coverage differ by regime? ------------------------
    rows = []
    for h in HORIZONS:
        f_nested = REPORTS / f"nested_h{h}.csv"
        f_int = REPORTS / f"intervals_h{h}.csv"
        if not f_nested.exists() or not f_int.exists():
            continue
        n = pd.read_csv(f_nested)
        m = pd.read_csv(f_int)[["origin", "lgbm_c80_lo", "lgbm_c80_hi",
                                "ar_c80_lo", "ar_c80_hi"]]
        d = n.merge(m, on="origin", how="left")
        d["i"] = d["origin"].str[:4].astype(int) * 12 + d["origin"].str[5:7].astype(int)
        d = d.merge(reg[["i", "p_high_vol"]], on="i", how="left").dropna(subset=["p_high_vol"])
        d["turbulent"] = d["p_high_vol"] > 0.5
        d["err_ar"] = (d["ar"] - d["actual"]).abs()
        d["err_nested"] = (d["lgbm_nested"] - d["actual"]).abs()
        from scipy import stats
        rec = {"h": h}
        for label, mask in (("calm", ~d["turbulent"]), ("turbulent", d["turbulent"])):
            sub = d[mask]
            ok = sub["lgbm_c80_lo"].notna()
            cov = float(((sub.loc[ok, "actual"] >= sub.loc[ok, "lgbm_c80_lo"]) &
                         sub.loc[ok, "actual"] <= sub.loc[ok, "lgbm_c80_hi"]).mean()) if ok.sum() else np.nan
            rec[f"n_{label}"] = int(len(sub))
            rec[f"err_{label}"] = round(float(sub["err_ar"].mean()), 2) if len(sub) else None
            rec[f"cov80_{label}"] = round(cov, 3) if cov == cov else None
            rec[f"width_{label}"] = round(float((sub["lgbm_c80_hi"] - sub["lgbm_c80_lo"]).mean()), 2) if ok.sum() else None
        a, b = d.loc[~d["turbulent"], "err_ar"].dropna(), d.loc[d["turbulent"], "err_ar"].dropna()
        rec["mwu_p"] = round(float(stats.mannwhitneyu(a, b, alternative="two-sided").pvalue), 3) \
            if len(a) > 3 and len(b) > 3 else None
        rows.append(rec)

    out = pd.DataFrame(rows)
    out.to_csv(REPORTS / "regime_vs_error.csv", index=False)
    print(out.to_string(index=False))

    # ---- report ---------------------------------------------------------
    share = float(reg["p_high_vol"].gt(0.5).mean())
    lines = ["# Volatility regimes and their effect on forecast error", "",
             f"Two-state Markov-switching AR with state-dependent variance, fitted on an expanding "
             f"window ({MIN_FIT}+ months before the first label). {len(reg)} months labelled, "
             f"{share:.1%} of them in the turbulent state.", "",
             "The regime label uses only data available at that month, so it is a real-time label, "
             "not a full-sample smoother that a backtest could not have had.", "",
             "## Error and interval coverage by regime", "",
             out.to_markdown(index=False), "",
             "`calm_vs_turbulent_p` is a Mann-Whitney test on the absolute AR errors of the two states.", "",
             "## Why this matters more than the point forecast", "",
             "If nominal-80% conformal intervals cover roughly 80% in the calm state and materially",
             "less in the turbulent state, then a single fixed-width interval is mis-specified by",
             "construction, and the fix is a regime-conditional width - which is a defensible,",
             "testable design choice rather than a modelling flourish.",
             ]
    (REPORTS / "regime.md").write_text("\n".join(lines), encoding="utf-8")
    print("\nwrote reports/regime.md")


if __name__ == "__main__":
    main()
