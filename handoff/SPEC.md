# SPEC - the technical contract

Everything below is a decision already made and validated. Change one only if you can state why,
and then report both the old and new numbers.

## 1. Target

`ipi_growth_yoy` - Industrial Production Index, total, year-on-year growth, percent.

Why this target: monthly frequency (so 1/3/6/12-month horizons are real), known publication lag,
enough history, and a narrower claim than "predicting recessions". Secondary targets, if you want
them: manufacturing IPI growth, headline CPI inflation, unemployment rate.

## 2. Horizons

h in {1, 3, 6, 12} months. A forecast made at origin `T` (known at end of month `T`) predicts the
value at month `T + h`.

## 3. The mask (publication lags)

`data/publication_lag.csv` gives `lag_months` per column. At origin `T`, column `s` may only use
observations up to month `T - lag_months(s)`.

| lag | columns | why |
|---|---|---|
| 0 | `opr`, `opr_changed_in_month` | MPC decision published 3 p.m. decision day |
| 1 | `cpi_*`, `exports_*`, `imports_*`, `trade_balance_rm_mil`, `myr_per_usd` | CPI ~3-4 weeks, trade ~4-5 weeks, monthly FX mean completes at month end |
| 2 | `ipi_*`, `ppi_growth_yoy`, `u_rate`, `p_rate`, `lf_employed` | IPI/PPI ~2 months, LFS ~5-6 weeks |
| 3 | `li_*` (DOSM leading/coincident/lagging) | Malaysian Economic Indicators |
| 4 | `blr`, `fdr_*`, `m2_rm_mil`, `m3_rm_mil` | BNM monthly banking statistics |

**Consequence to state in your report:** with `T = 2026-10`, the newest usable IPI is `2026-08`, so
a "1-month-ahead" forecast is really a forecast of `2026-11` - three months past the newest data.

## 4. Feature contract (the set that was tested)

| feature | source column | lag used | note |
|---|---|---|---|
| `ipi_yoy_l1..l3, l6, l12` | `ipi_growth_yoy` | lag 2 + 1/2/3/6/12 | target's own memory |
| `exp_yoy_l1, l2, l12` | `exports_growth_yoy` | lag 1 + offsets | external demand channel |
| `cpi_yoy`, `cpi_yoy_l2` | `cpi_inflation_yoy` | lag 1 + offset | |
| `u_rate` | `u_rate` | lag 2 | labour slack |
| `ppi_yoy` | `ppi_growth_yoy` | lag 2 | upstream prices |
| `li_diff` | `li_leading_diffusion` | lag 3 | breadth of expansion |
| `opr` | `opr` | lag 0 | policy rate |
| `myr_usd_l1` | `myr_per_usd` | lag 1 + 1 | exchange rate |

**Collinearity discovered in the data** (drop one of each pair): `blr`↔`opr` r=0.996,
`m2`↔`m3` r=1.000, `fdr_1mo`↔`fdr_3mo` r=0.998, `ipi_index`↔`ipi_manufacturing_index` r=0.992.
87 pairs at |r| >= 0.8 in total. Never put both members of a pair in a model.

## 5. Validation protocol

- Expanding window, rolling origin. At each origin, training data = all pairs strictly before it.
- Minimum 36 training pairs (`MIN_TRAIN`). Report the number of origins per horizon.
- Baseline set, all on the same origins: random walk (last visible value), mean of last 3,
  AR(p) with p chosen by AIC (p in 0..4, iterated forward), and - for the multistep work - a
  direct multi-step ARDL and a VAR with a stability guard.
- Metrics: MAE, RMSE, MASE (MAE / random-walk MAE), bias. Plus Diebold-Mariano on squared errors
  with Newey-West variance at lag h-1.

## 6. Model ladder (this order, and report all of them)

1. Random walk, mean-of-3, AR(AIC)  ← the bar
2. LightGBM on lagged features, four declared configurations (default / regularised / heavily
   regularised / linear-tree leaves), nested selection
3. AR-X: direct multi-step ARDL on the 7 features above
4. VAR(2) on (target, export growth, OPR) with an explicit stability guard: if the companion roots
   indicate instability, refuse to issue that forecast and count it
5. Probabilistic: (a) AR normal intervals, (b) quantile LightGBM at 5/10/50/90/95, (c) conformal -
   point forecast +/- the empirical quantile of PAST errors only
6. Regime: two-state Markov-switching AR with state-dependent variance, standardised inside each
   expanding window, filtered probabilities only (real-time label)

## 7. What was found (so you know what "correct" looks like)

- AR(AIC) beats LightGBM at every horizon **once selection is nested**. Stock hyperparameters made
  LightGBM lose badly; post-hoc tuning made it look like it won; nested selection removed the win.
- AR-X wins at **h=1**: MASE 0.591 vs AR 0.758 on matched origins (DM p=0.063 matched, 0.007 full).
  Its advantage is concentrated in the 20 turbulent post-COVID origins.
- VAR requires the stability guard: 20 of 91 origins produced exploding iterates (-674 pp, -4974 pp)
  while the median forecast stayed at 3.0 pp.
- Quantile LightGBM **under-covers** (0.64 at nominal 0.80). Conformal **over-covers** (0.88-0.93)
  and wins on pinball loss.
- Forecast error is **2.4x larger in the turbulent volatility state** at h=1 (3.23 -> 7.84 pp,
  MWU p=0.006) and 2.3x at h=12, but the effect reverses at h=6 and the turbulent cell holds only
  10 origins.

## 8. Interpretability constraints found the hard way

- AR-X at h=1 has **R² = 0.052** on 122 observations. It beats the AR anyway. Report both facts.
- `opr` takes only **6 distinct values** in the sample, so its coefficient is a rate-regime
  indicator, not an elasticity. A 25 bp move appearing to shift the forecast 0.29 pp rests on six
  observations. Never present that as a policy experiment.
- At one point the two specifications disagreed by 3.3 pp at h=1. Surface that disagreement in the
  app rather than showing one number.

## 9. App requirements

Per horizon: point forecast, the competing baseline beside it, the 80% interval **and its width**,
P(y < 0) from a normal approximation using the conformal width, backtest MAE, and the current
regime label with its measured error penalty. Scenario sliders through the AR-X channel, labelled
as a sensitivity check. A downloadable brief. Every caveat on the page, not in a footnote.
