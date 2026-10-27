#!/usr/bin/env python3
"""
ML Economic 1 (Ajey) - step 5: exploratory analysis with the tests that actually decide things.

Not a plot dump. Four questions, each with a test behind it:

  Q1  Is each series stationary, and on what transform should the target be modelled?
      -> ADF (unit root) + KPSS (stationarity) run in opposite directions. One test alone
         is a weak-power trap on a 140-month sample.
  Q2  Is there a structural break that invalidates a single-regime model?
      -> Chow test at 2020-03 (COVID) and at 2026-04 (export surge), plus CUSUM stability.
  Q3  Are DOSM's seasonally adjusted values better than the NSA ones for modelling?
      -> compare residual seasonality and variance.
  Q4  Which predictors are collinear enough to be redundant?
      -> correlation matrix, flagging |r| >= 0.8.

Output: reports/eda.md  (tables only, so the numbers can be quoted directly)

Usage: python scripts/eda.py
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox, breaks_cusumolsresid
from statsmodels.stats.stattools import durbin_watson
from statsmodels.tsa.stattools import adfuller, kpss
import statsmodels.api as sm

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

TARGET = "ipi_growth_yoy"


def load() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / "panel_monthly.csv", dtype={"month": str})
    df["date"] = pd.to_datetime(df["month"] + "-01")
    return df.set_index("date").drop(columns=["month", "opr_changed_in_month"], errors="ignore")


def stationarity_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in df.columns:
        s = df[col].dropna()
        if len(s) < 40 or s.nunique() < 10:
            continue
        try:
            adf_p = adfuller(s, autolag="AIC")[1]
        except Exception:
            adf_p = np.nan
        try:
            kpss_p = kpss(s, regression="c", nlags="auto")[1]
        except Exception:
            kpss_p = np.nan
        # agreement: ADF rejects unit root AND KPSS does not reject stationarity
        verdict = "-"
        if not np.isnan(adf_p) and not np.isnan(kpss_p):
            if adf_p < 0.05 and kpss_p > 0.05:
                verdict = "stationary"
            elif adf_p > 0.05 and kpss_p < 0.05:
                verdict = "unit root"
            else:
                verdict = "ambiguous"
        rows.append({"column": col, "n": len(s), "adf_p": round(adf_p, 3) if not np.isnan(adf_p) else None,
                     "kpss_p": round(kpss_p, 3) if not np.isnan(kpss_p) else None, "verdict": verdict})
    return pd.DataFrame(rows).sort_values("verdict")


def chow_test(df: pd.DataFrame, col: str, break_date: str, lags: int = 2) -> dict:
    """Chow test for a break in an AR(lags) regression on `col`."""
    s = df[col].dropna()
    d = pd.DataFrame({f"lag{i}": s.shift(i) for i in range(1, lags + 1)})
    d["y"] = s
    d = d.dropna()
    brk = pd.Timestamp(break_date)
    if brk <= d.index[0] or brk >= d.index[-1]:
        return {}
    d1, d2 = d[d.index < brk], d[d.index >= brk]
    if len(d1) < lags + 5 or len(d2) < lags + 5:
        return {}
    X = sm.add_constant(d.drop(columns="y"))
    rss_p = sm.OLS(d["y"], X).fit().ssr
    rss_1 = sm.OLS(d1["y"], sm.add_constant(d1.drop(columns="y"))).fit().ssr
    rss_2 = sm.OLS(d2["y"], sm.add_constant(d2.drop(columns="y"))).fit().ssr
    k = X.shape[1]
    n = len(d)
    df1, df2 = k, n - 2 * k
    if df2 <= 0:
        return {}
    f = ((rss_p - (rss_1 + rss_2)) / df1) / ((rss_1 + rss_2) / df2)
    from scipy import stats
    p = 1 - stats.f.cdf(f, df1, df2)
    return {"break": break_date, "n_before": len(d1), "n_after": len(d2),
            "F": round(float(f), 3), "p": round(float(p), 4),
            "break_significant": bool(p < 0.05)}


def seasonality_check(df: pd.DataFrame) -> pd.DataFrame:
    """Does the NSA series still carry residual seasonality that the SA series removed?"""
    rows = []
    pairs = [("ipi_index", "ipi_index_sa"), ("ipi_growth_yoy", None)]
    for nsa, sa in pairs:
        s_nsa = df[nsa].dropna()
        m = s_nsa.groupby(s_nsa.index.month).mean()
        spread_nsa = (m.max() - m.min()) / abs(s_nsa.mean()) * 100
        lb_nsa = acorr_ljungbox(s_nsa.diff().dropna(), lags=[12], return_df=True)["lb_pvalue"].iloc[0]
        row = {"series": nsa, "seasonal_spread_pct": round(spread_nsa, 2),
               "ljungbox_p_12": round(float(lb_nsa), 4), "var": round(float(s_nsa.var()), 2)}
        if sa:
            s_sa = df[sa].dropna()
            m2 = s_sa.groupby(s_sa.index.month).mean()
            row["sa_seasonal_spread_pct"] = round((m2.max() - m2.min()) / abs(s_sa.mean()) * 100, 2)
            row["sa_var"] = round(float(s_sa.var()), 2)
        rows.append(row)
    return pd.DataFrame(rows)


def collinearity(df: pd.DataFrame, thresh: float = 0.8) -> pd.DataFrame:
    cols = [c for c in df.columns if df[c].notna().sum() > 100]
    corr = df[cols].corr()
    pairs = []
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            r = corr.loc[a, b]
            if pd.notna(r) and abs(r) >= thresh:
                pairs.append({"series_a": a, "series_b": b, "r": round(float(r), 3)})
    return pd.DataFrame(pairs).sort_values("r", key=abs, ascending=False)


def main() -> None:
    df = load()
    out = ["# Exploratory analysis - ML Economic 1 (Ajey)", "",
           f"Panel: {df.shape[0]} months, {df.shape[1] - 1} series, "
           f"{df.index.min():%Y-%m} to {df.index.max():%Y-%m}.", ""]

    st = stationarity_table(df)
    out += ["## Q1. Stationarity: ADF (H0 = unit root) vs KPSS (H0 = stationary)", "",
            "Both tests must agree before a series is declared I(0) or I(1).", "",
            st.to_markdown(index=False), ""]
    counts = st["verdict"].value_counts().to_dict()
    out += [f"Verdict counts: {counts}", ""]

    out += ["## Q2. Structural breaks in the AR(2) dynamics of the target", ""]
    breaks = []
    for col in ("ipi_growth_yoy", "exports_growth_yoy", "cpi_inflation_yoy"):
        for d in ("2020-03-01", "2021-06-01", "2026-04-01"):
            r = chow_test(df, col, d)
            if r:
                r = {"series": col, **r}
                breaks.append(r)
    if breaks:
        out += [pd.DataFrame(breaks).to_markdown(index=False), ""]

    # CUSUM stability on the target's AR(2)
    s = df[TARGET].dropna()
    d = pd.DataFrame({"lag1": s.shift(1), "lag2": s.shift(2), "y": s}).dropna()
    res = sm.OLS(d["y"], sm.add_constant(d[["lag1", "lag2"]])).fit()
    cusum = breaks_cusumolsresid(res.resid)
    out += ["## Q3. Parameter stability (CUSUM) on the target AR(2)", "",
            f"CUSUM statistic = {cusum[0]:.3f}, p = {cusum[1]:.4f} "
            f"({'reject' if cusum[1] < 0.05 else 'cannot reject'} stable parameters); "
            f"Durbin-Watson = {durbin_watson(res.resid):.2f}.", ""]

    sea = seasonality_check(df)
    out += ["## Q4. Seasonality: is DOSM's SA series actually smoother?", "",
            sea.to_markdown(index=False), ""]

    col = collinearity(df)
    out += ["## Q5. Collinear pairs (|r| >= 0.8) - drop one from each pair", "",
            (col.head(25).to_markdown(index=False) if not col.empty else "none"), ""]

    (REPORTS / "eda.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out[:12]))
    print(f"\nwrote reports/eda.md ({len(st)} series tested, {len(col)} collinear pairs)")


if __name__ == "__main__":
    main()
