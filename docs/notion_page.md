**Malaysian Macroeconomic Intelligence Engine** - a research-grade forecasting system, not a dashboard.

**Project code:** ML Economic 1 (Ajey) · **Owner:** Azam Azhan · **Started:** 2026-10-26
**Repo (local):** `C:\Users\User\Projects\ml-economic-1`

## 1. The question this answers

Can Malaysia's economic conditions 3-12 months ahead be forecast with a system that survives technical interrogation - not just a model with a good-looking score?

Three specific, defensible outputs:

<callout icon="🎯" color="blue_bg">
	**Primary target: industrial production growth (IPI, yoy) at horizons h = 1, 3, 6 and 12 months.**
	Industrial production is monthly, published with a known lag, and has enough history to backtest honestly. "Predicting recessions" is not the claim - the claim is narrower and stronger.
</callout>

Supporting outputs: regime identification (expansion / slowdown / high-inflation), scenario shocks (inflation up, exports down, OPR change), and calibrated prediction intervals.

## 2. Locked decisions

- **Target:** `ipi_growth_yoy`, horizons 1, 3, 6, 12 months. Secondary: manufacturing IPI growth, CPI inflation, unemployment rate.
- **Sample:** 2015-01 onward (140 monthly observations) - forced by the IPI 2015=100 rebasing. Long-run diagnostics may use CPI from 1980 and trade from 1990, but never for training.
- **Baselines must win first:** random walk, seasonal naive, ARIMA, VAR. A model is only reported as "better" if it beats them on the identical rolling-origin split.
- **No deep learning.** LightGBM/XGBoost with disciplined features; the credibility comes from validation, not architecture.
- **Honest reporting:** if ML loses to ARIMA, the report says ML lost. That is a finding.

## 3. Data - what already exists (verified, not planned)

13 official catalogues pulled from `api.data.gov.my` plus the BNM OPR decision history. Panel: **142 months x 33 series**, 2015-01 to 2026-10, plus 46 quarters of GDP.

- **Production:** IPI total (NSA + SA + mom + yoy), mining / manufacturing / electricity sections
- **Prices:** CPI headline (mom, yoy), food (div 01), housing (div 04), core CPI
- **Labour:** unemployment rate, participation rate, employed persons (seasonally adjusted)
- **External:** exports, imports, trade balance, growth rates (RM million)
- **Money & rates:** OPR (full MPC decision history 2004-2026), BLR, FDR 1m/3m, M2, M3, MYR/USD
- **Leading indicators:** DOSM leading, coincident, lagging index + diffusion
- **Output:** real GDP seasonally adjusted (quarterly)

Three integrity checks passed in the build:

- Exports 2026-04 to 2026-09 identical across two independent catalogues (0.000% difference) - so the +54.5% yoy export surge is real, not a parsing error
- Trade series arrive in ringgit, converted to RM million; 2015-01 = RM 62.97b matches the official release
- CPI "overall" is genuinely distinct from division 01 (differs in ~97% of months) - no component mis-mapping

## 4. Leakage control - the part that makes this research-grade

<callout icon="⚠️" color="red_bg">
	A forecast made at the end of month T may only use series values published by then. Malaysia's release lags differ by series: CPI ~3 weeks, IPI ~2 months, BNM monetary statistics ~4 months. Ignoring this is the single most common way a macro forecast backtest becomes fiction.
</callout>

- Every series carries a `lag_months`, established from what the official API actually holds today and cross-checked against each agency's documented release practice
- One enforcement function (`available_asof`) truncates the panel; nothing bypasses it
- A pre-build check asserts no column exceeds its cutoff. At origin 2026-08 it withholds 51 observations that a naive build would have used
- Live consequence: with T = 2026-10, the newest usable IPI is 2026-08, so a "1-month-ahead" forecast is really a forecast of 2026-11 - three months past the newest data. That is the real task.
- **Not solved:** revisions. Malaysia has no public real-time vintage database, so results use a fixed vintage with a documented +/-0.3pp sensitivity band. Stated as a limitation, not hidden.

## 5. Build plan (8 weeks, adjusted to the data)

<details color="gray">
<summary>Week 1 - Data foundation (DONE in session 1)</summary>
	13 catalogues + OPR history acquired; panel built; dictionary written; publication-lag mask enforced; availability self-check passing.
</details>

<details color="gray">
<summary>Week 2 - Exploratory analysis</summary>
	Stationarity (ADF/KPSS), structural breaks, correlation structure among the 33 series, target selection robustness, seasonality check on the SA vs NSA gap.
</details>

<details color="gray">
<summary>Week 3 - Econometric baselines</summary>
	Random walk, seasonal naive, ARIMA on levels and differences, VAR with lag selection. Rolling-origin scores. These numbers are the bar everything else must clear.
</details>

<details color="gray">
<summary>Week 4 - Machine learning</summary>
	Lagged features built strictly inside the availability mask; LightGBM; expanding-window validation; feature-count discipline against 140 observations.
</details>

<details color="gray">
<summary>Week 5 - Uncertainty and regimes</summary>
	Quantile regression and conformal intervals; calibration checks (are 80% intervals actually 80%?); Hidden Markov Model or change-point detection for regimes; comparison against baselines.
</details>

<details color="gray">
<summary>Week 6 - Explanation and scenarios</summary>
	SHAP with correct interpretation (correlation is not causation, and lags inflate apparent importance); explicit shock definitions (inflation +1pp, exports -10%, OPR +/-25bp) propagated through the model.
</details>

<details color="gray">
<summary>Week 7 - Application</summary>
	Python API + Streamlit app: forecast with intervals, risk signal, scenario panel, explanations, downloadable report. Automated refresh that re-runs the availability check before anything is shown.
</details>

<details color="gray">
<summary>Week 8 - Report and portfolio</summary>
	Model comparison on honest out-of-sample results, limitations section, reproducible experiment log, README, 3-minute demo video.
</details>

## 6. Deliverables

- Cleaned, documented dataset with a re-runnable pipeline (two commands, no manual steps)
- Model comparison report with rolling-origin results and baselines included even where they win
- Leakage policy a reviewer can audit
- Deployed forecasting application with intervals and scenarios
- Technical report: methodology, limitations, findings, recommendations
- Recruiter-facing demo video

## 7. Risks, stated up front

- **Small sample.** 140 months; at h=12 the effective training set is ~123 pairs. Expect ML to be close to ARIMA, not far ahead. The value is in intervals, regimes and leakage discipline.
- **Structural break in progress.** Export growth +45% yoy through 2026 is a regime the model has never seen; the regime component must be able to say "out of distribution".
- **Revision risk** on GDP levels; IPI growth is safer.
- **Overfitting temptation.** Feature engineering is where the hours go and where leakage returns. The mask, not discipline, is the defence.

## 8. Status log

- **2026-10-26** - Notion project created. Session 1: data acquisition (13 catalogues + BNM OPR), 142-month panel, data dictionary with verified checkpoints, publication-lag mask + availability self-check passing, leakage policy written. Next: exploratory analysis (Week 2).
