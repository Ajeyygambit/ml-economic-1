#!/usr/bin/env python3
"""
ML Economic 1 (Ajey) - decision-support app.

Design rule: the app publishes what survived validation, and it publishes the caveats with
the numbers rather than in a footnote.

  * point forecast  - AR-X at h=1 (the only horizon where anything beats the AR), AR(AIC) at h=3/6/12
  * interval        - conformal: +/- the empirical quantile of PAST errors at that horizon
  * risk signal     - P(growth < 0) from a normal approximation using that conformal width
  * regime          - real-time Markov-switching volatility state, with the measured error penalty
  * scenarios       - AR-X channel: exports, CPI, OPR shocked, refitted and re-predicted
  * download        - the whole thing as a markdown brief

Run:  streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import streamlit as st
from scipy import stats as sps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mlcore import ar_forecast, build_features, load_panel  # noqa: E402

HORIZONS = (1, 3, 6, 12)
CHAMPION = {1: "AR-X (ARDL: exports, CPI, OPR)", 3: "AR(AIC)", 6: "AR(AIC)", 12: "AR(AIC)"}
TARGET_LABEL = "Industrial production growth (IPI, yoy)"

# measured in scripts/regime.py - error ratio turbulent/calm at h=1
REGIME_ERROR_MULTIPLIER = 2.4
SAMPLE_MONTHS = 142


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_all():
    panel, y = load_panel()
    F = build_features(panel)
    errors = {}
    for h in HORIZONS:
        f = ROOT / "reports" / f"arx_var_h{h}.csv"
        d = pd.read_csv(f)
        errors[h] = {"ar": np.abs(d["ar"] - d["actual"]).dropna().values,
                     "arx": np.abs(d["arx"] - d["actual"]).dropna().values}
    reg = pd.read_csv(ROOT / "reports" / "regime_probabilities.csv")
    audit = pd.read_csv(ROOT / "reports" / "intervals_summary.csv")
    model_cmp = pd.read_csv(ROOT / "reports" / "arx_var_summary.csv")
    return panel, y, F, errors, reg, audit, model_cmp


def origin_row(F: pd.DataFrame) -> int:
    """Latest month whose full feature row is observable - i.e. today's forecast origin."""
    ok = F.dropna()
    return int(ok.index.max())


@st.cache_resource(show_spinner=False)
def fit_arx(panel: pd.DataFrame, h: int):
    """Direct multi-step ARDL, fitted on everything visible now."""
    y = panel["ipi_growth_yoy"]
    X = pd.DataFrame({
        "y_l1": y.shift(3), "y_l2": y.shift(4), "y_l3": y.shift(5),
        "exp_l1": panel["exports_growth_yoy"].shift(2),
        "exp_l2": panel["exports_growth_yoy"].shift(3),
        "cpi_l1": panel["cpi_inflation_yoy"].shift(1),
        "opr": panel["opr"],
    })
    train = X.join(y.shift(-h).rename("__y")).dropna()
    return sm.OLS(train["__y"], sm.add_constant(train.drop(columns="__y"))).fit(), X


def predict_arx(model, X: pd.DataFrame, origin: int, row=None) -> float:
    x = (X.loc[[origin]] if row is None else pd.DataFrame([row])).copy()
    return float(np.asarray(model.predict(sm.add_constant(x, has_constant="add")))[0])


def conformal_halfwidth(errors: np.ndarray, level: float) -> float:
    return float(np.quantile(errors, level))


def arx_diagnostics(panel: pd.DataFrame, origin: int, h: int) -> dict:
    """R2, out-of-range features and the number of distinct policy-rate values.

    These exist because a positive coefficient in a 0.05-R2 regression is not an elasticity,
    and an app that lets a user drag a slider must say so.
    """
    y = panel["ipi_growth_yoy"]
    X = pd.DataFrame({
        "y_l1": y.shift(3), "y_l2": y.shift(4), "y_l3": y.shift(5),
        "exp_l1": panel["exports_growth_yoy"].shift(2),
        "exp_l2": panel["exports_growth_yoy"].shift(3),
        "cpi_l1": panel["cpi_inflation_yoy"].shift(1),
        "opr": panel["opr"],
    })
    train = X.join(y.shift(-h).rename("__y")).dropna()
    model = sm.OLS(train["__y"], sm.add_constant(train.drop(columns="__y"))).fit()
    row = X.loc[origin]
    outside = {c: (float(row[c]), float(train[c].min()), float(train[c].max()))
               for c in X.columns if row[c] < train[c].min() or row[c] > train[c].max()}
    return {"r2": float(model.rsquared), "n_obs": int(model.nobs),
            "opr_distinct": int(panel["opr"].dropna().nunique()), "outside": outside}


# --------------------------------------------------------------------------
# pages
# --------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="Malaysia Macro Forecast - ML Economic 1", page_icon="📈",
                       layout="wide")

    panel, y, F, errors, reg, audit, model_cmp = load_all()
    origin = origin_row(F)
    origin_label = f"{origin // 12}-{origin % 12 or 12:02d}"
    latest_y = float(y.loc[:origin].dropna().iloc[-1])
    latest_y_month = y.loc[:origin].dropna().index[-1]
    p_high = float(reg["p_high_vol"].iloc[-1])
    turbulent = p_high > 0.5

    st.title("📈 Malaysian macro - IPI growth forecast")
    st.caption(f"{TARGET_LABEL} · forecast origin **{origin_label}** (end of month, "
               f"publication lags respected) · data vintage {date.today():%Y-%m-%d}")

    # ---------------- headline: all four horizons -------------------------
    rows = []
    for h in HORIZONS:
        champ = "arx" if h == 1 else "ar"
        if h == 1:
            model, X = fit_arx(panel, h)
            point = predict_arx(model, X, origin)
        else:
            point = ar_forecast(y, origin, h)
        ar_bench = ar_forecast(y, origin, h)
        q80 = conformal_halfwidth(errors[h][champ], 0.80)
        q95 = conformal_halfwidth(errors[h][champ], 0.95)
        sigma = q80 / 1.2816 if q80 else np.nan
        p_neg = float(sps.norm.cdf((0 - point) / sigma)) if sigma else np.nan
        target_month = origin + h
        rows.append({
            "horizon": f"+{h} mo",
            "for month": f"{target_month // 12}-{target_month % 12 or 12:02d}",
            "model": CHAMPION[h],
            "forecast (pp)": round(point, 2),
            "AR(AIC) (pp)": round(float(ar_bench), 2) if ar_bench == ar_bench else None,
            "80% low": round(point - q80, 1),
            "80% high": round(point + q80, 1),
            "width (pp)": round(2 * q80, 1),
            "P(growth < 0)": f"{p_neg:.0%}" if p_neg == p_neg else "-",
            "MAE in backtest (pp)": round(float(np.mean(errors[h][champ])), 2),
        })
    table = pd.DataFrame(rows)

    st.subheader("Forecast")
    cols = st.columns(4)
    for c, r in zip(cols, rows):
        c.metric(label=f"{r['horizon']} → {r['for month']}", value=f"{r['forecast (pp)']:+.1f} pp")
        c.caption(f"80%: {r['80% low']:+.1f} to {r['80% high']:+.1f} pp · "
                  f"P(&lt;0) = {r['P(growth < 0)']}")
    st.dataframe(table, hide_index=True, width="stretch")

    diag1 = arx_diagnostics(panel, origin, 1)
    gap = abs(rows[0]["forecast (pp)"] - (rows[0]["AR(AIC) (pp)"] or 0))
    if gap > 1.0:
        st.warning(f"**The two specifications disagree at h=1 by {gap:.1f} pp** "
                   f"(AR-X {rows[0]['forecast (pp)']:+.1f} vs AR {rows[0]['AR(AIC) (pp)']:+.1f}). "
                   f"The AR-X wins in backtest but explains only R² = {diag1['r2']:.2f} of the "
                   f"variance, so its level is driven by the intercept and the policy-rate term "
                   f"rather than by the export channel. Treat the h=1 point forecast as the "
                   f"less reliable of the four, not the most.")
    if diag1["outside"]:
        st.error("Current inputs fall outside the training range for "
                 + ", ".join(f"`{k}` = {v[0]:.1f} (train {v[1]:.1f} to {v[2]:.1f})"
                             for k, v in diag1["outside"].items())
                 + " — the linear model is extrapolating and the forecast should not be trusted.")
    st.caption(f"Latest observed value: **{latest_y:+.2f} pp** "
               f"({latest_y_month // 12}-{latest_y_month % 12 or 12:02d}). "
               f"Interval widths above are the champion model's own conformal widths; against "
               f"a series with a standard deviation of 6.6 pp they are wide, and the app does "
               f"not pretend otherwise.")

    # ---------------- regime + trust -------------------------------------
    left, right = st.columns([1, 1])

    with left:
        st.subheader("Current regime")
        if turbulent:
            st.error(f"**Turbulent volatility state** (p = {p_high:.0%}). "
                     f"In the backtest, forecast error was ~{REGIME_ERROR_MULTIPLIER}x larger "
                     f"in this state at h=1 (3.23 pp -> 7.84 pp, Mann-Whitney p = 0.006).")
        else:
            st.success(f"**Calm volatility state** (p of turbulent = {p_high:.0%}). "
                       f"Measured error in this state: 3.2 pp at h=1.")
        st.caption("Two-state Markov-switching AR, state-dependent variance, fitted on an "
                   "expanding window so the label is real-time - not a full-sample smoother "
                   "a backtest could not have had. The effect is not monotone across horizons "
                   "(at h=6 the direction reverses), so treat it as context, not a coefficient.")

    with right:
        st.subheader("How much to trust this")
        st.markdown(
            f"""
- **Sample:** {SAMPLE_MONTHS} months (2015-01 onward). At h=12 the effective training
  set is ~54 origin pairs. Small.
- **Model ranking, Diebold-Mariano:** AR-X beats AR at h=1 (p = 0.063 on matched origins,
  0.007 on all); everywhere else the difference is inside the noise floor.
- **Interval calibration:** at a nominal 80%, quantile LightGBM delivered 0.64 coverage,
  conformal delivered 0.88-0.93. Nothing landed on 0.80, and this sample cannot verify it
  to better than about ±5 pp.
- **What is enforced:** every input respects the publication lag in
  `data/publication_lag.csv` — IPI arrives with a 2-month lag, so at origin {origin_label}
  the newest usable IPI is 2026-06.
"""
        )
        st.info("Revisions are not modelled: Malaysia has no public real-time vintage "
                "database, so these are fixed-vintage results with a documented limitation, "
                "not a solved problem.")

    # ---------------- scenarios ------------------------------------------
    st.subheader("Scenario analysis")
    st.caption("The AR models have no exogenous channel, so scenarios run through the AR-X "
               "specification - the champion at h=1, a reasonable reduced form elsewhere. "
               "Shocks are applied to the latest visible values and the model is re-predicted.")
    sc1, sc2, sc3, sc4 = st.columns(4)
    h_sel = sc1.selectbox("Horizon", HORIZONS, index=0, format_func=lambda h: f"+{h} months")
    d_exp = sc2.slider("Export growth (pp)", -40.0, 40.0, 0.0, 1.0)
    d_cpi = sc3.slider("CPI inflation (pp)", -2.0, 4.0, 0.0, 0.1)
    d_opr = sc4.slider("OPR (basis points)", -100, 100, 0, 25)

    model_s, X_s = fit_arx(panel, h_sel)
    base_row = X_s.loc[origin].copy()
    shocked = base_row.copy()
    for col in ("exp_l1", "exp_l2"):
        shocked[col] = shocked[col] + d_exp
    shocked["cpi_l1"] = shocked["cpi_l1"] + d_cpi
    shocked["opr"] = shocked["opr"] + d_opr / 100.0

    base = predict_arx(model_s, X_s, origin)
    scen = predict_arx(model_s, X_s, origin, row=shocked)
    q80s = conformal_halfwidth(errors[h_sel]["arx"], 0.80)

    s1, s2, s3 = st.columns(3)
    s1.metric("Baseline forecast", f"{base:+.2f} pp")
    s2.metric("Under scenario", f"{scen:+.2f} pp", delta=f"{scen - base:+.2f} pp")
    s3.metric("Scenario 80% interval",
              f"{scen - q80s:+.1f} to {scen + q80s:+.1f} pp")
    if abs(scen - base) < 0.05:
        st.caption("The shocks you have set barely move the forecast — the AR-X channel is "
                   "weak outside crisis periods, which is consistent with the finding that its "
                   "advantage is concentrated in the turbulent post-COVID origins.")
    diag_s = arx_diagnostics(panel, origin, h_sel)
    st.caption(f"AR-X coefficients used (h={h_sel}): "
               + ", ".join(f"{k} = {v:+.3f}" for k, v in model_s.params.items()
                           if k in {"exp_l1", "exp_l2", "cpi_l1", "opr"}))
    st.warning(
        f"**Read these coefficients as correlations, not elasticities.** The AR-X explains "
        f"R² = {diag_s['r2']:.2f} at this horizon on {diag_s['n_obs']} observations, and OPR "
        f"takes only {diag_s['opr_distinct']} distinct values in the sample — so the policy-rate "
        f"term behaves as a regime indicator, and the +/-100 bp slider moves the forecast by "
        f"about 1.2 pp on the strength of six data points. The scenario is a sensitivity check "
        f"inside the estimated relationship, not a policy experiment."
    )

    # ---------------- model comparison + download ------------------------
    with st.expander("Model comparison (out-of-sample, rolling origin)"):
        st.dataframe(model_cmp[["h", "n_origins", "ar_MASE", "arx_MASE", "var_MASE",
                                "var_origins_stable", "arx_vs_ar_p"]],
                     hide_index=True, width="stretch")
        st.caption("MASE is relative to the random walk; below 1 beats 'tomorrow looks like "
                   "today'. `var_origins_stable` shows how many origins the VAR could be "
                   "trusted at - 20 were rejected by the stability guard because the iterates "
                   "exploded to -673 pp and -4974 pp.")

    with st.expander("Coverage audit (does the interval keep its promise?)"):
        keep = ["h", "n_origins", "ar_normal_80_coverage", "lgbm_quantile_80_coverage",
                "lgbm_conformal_80_coverage", "ar_normal_95_coverage",
                "lgbm_conformal_95_coverage"]
        st.dataframe(audit[[c for c in keep if c in audit.columns]].rename(columns={
            "ar_normal_80_coverage": "AR normal 80%",
            "lgbm_quantile_80_coverage": "quantile LGBM 80%",
            "lgbm_conformal_80_coverage": "conformal 80%",
            "ar_normal_95_coverage": "AR normal 95%",
            "lgbm_conformal_95_coverage": "conformal 95%"}),
            hide_index=True, width="stretch")

    brief = ["# Malaysian macro forecast - brief", "",
             f"Origin: {origin_label}. Vintage: {date.today():%Y-%m-%d}. "
             f"Target: {TARGET_LABEL}.", "",
             "## Forecast", "", table.to_markdown(index=False), "",
             f"Current regime: {'TURBULENT' if turbulent else 'CALM'} (p_turbulent = {p_high:.2f}).", "",
             "## Scenario", "",
             f"Horizon {h_sel}: exports {d_exp:+.0f} pp, CPI {d_cpi:+.1f} pp, "
             f"OPR {d_opr:+d} bp -> {scen:+.2f} pp (baseline {base:+.2f} pp).", "",
             "## Caveats that travel with these numbers", "",
             f"- Sample: {SAMPLE_MONTHS} months; ~54 origin pairs at h=12.",
             "- Point-forecast differences beyond h=1 are not statistically distinguishable.",
             "- 80% intervals are 11-17 pp wide against a series sd of 6.6 pp.",
             "- Vintages, not revisions: fixed-vintage results, revision risk unquantified.",
             "- Publication lags are enforced; nothing published after the origin enters.",
             ]
    st.download_button("Download forecast brief (markdown)", "\n".join(brief),
                       file_name=f"ml-economic-1-brief-{origin_label}.md", mime="text/markdown")

    st.divider()
    st.caption("Model: AR-X / AR(AIC) · intervals: conformal · regime: Markov switching · "
               "code and reports: github.com/Ajeyygambit/ml-economic-1 (private)")


if __name__ == "__main__":
    main()
