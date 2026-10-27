# Model comparison - out-of-sample, honest

**Target:** `ipi_growth_yoy` (industrial production growth, year-on-year)
**Validation:** expanding-window rolling origin, 36+ training pairs required, origins from 2016-01 to 2026-08
**Masking:** every feature and the target respect `data/publication_lag.csv`; the target's own lag is 2 months
**Vintage:** download of 2026-10-26 (`data/manifest.json`)
**Code:** `scripts/backtest.py` (baselines + ML), `scripts/tune_lgbm.py` (ML sensitivity), `scripts/eda.py` (diagnostics)

---

## 1. What the diagnostics said first

| test | result | consequence |
|---|---|---|
| ADF + KPSS on `ipi_growth_yoy` | ADF p=0.020, KPSS p=0.10 → stationary | modelling the yoy transform is defensible; no differencing needed |
| ADF + KPSS on `ipi_index`, `ipi_manufacturing_index` | ADF p≈0.98, KPSS p=0.01 → I(1) | never regress levels on levels |
| Chow test, AR(2) coefficients, break at 2020-03 | F=0.27, p=0.85 → no break | COVID hit the level, not the dynamics - a constant-parameter model is not obviously wrong |
| CUSUM on the target's AR(2) | stat 0.97, p=0.31 | parameters stable over the sample |
| DOSM SA vs NSA (IPI) | seasonal spread 9.65% → 3.35%; variance 185.5 → 174.1 | DOSM's SA removes most, not all, seasonality |
| Collinearity | 87 pairs with \|r\| ≥ 0.8, incl. `blr`↔`opr` 0.996, `m2`↔`m3` 1.000 | feature set keeps OPR only, one FDR leg, no M2/M3 pair |

Two of these are worth saying out loud, because they contradict what one expects:

* **No structural break was detected in the target's dynamics**, so "everything changed after 2020" is not supported here - what changed was the level of activity, not how growth depends on its own past.
* **The Chow test is narrow**: it tests AR coefficients only, not a break in variance or in the mean. A regime model is still justified on those grounds; it just cannot be justified by this test.

## 2. Default configuration - the result before any tuning

MASE is relative to the random walk; < 1 means "beats assuming next month looks like today".

| h | n origins | RW MAE | AR(AIC) MAE | LightGBM MAE | AR MASE | LGBM MASE | LGBM-vs-AR (Diebold-Mariano) |
|---|---|---|---|---|---|---|---|
| 1 | 77 | 6.20 | 4.84 | 5.31 | 0.781 | 0.857 | p=0.656, no difference |
| 3 | 75 | 5.94 | 3.63 | 4.74 | 0.611 | 0.797 | p=0.253, no difference |
| 6 | 72 | 5.76 | 3.81 | 5.94 | 0.661 | 1.032 | **p=0.010, AR better** |
| 12 | 66 | 6.44 | 3.71 | 5.07 | 0.577 | 0.788 | p=0.094, AR better (marginal) |

Read plainly: with stock hyperparameters, LightGBM is **worse than a univariate AR** at every horizon, significantly so at h=6, and at h=6 it fails to beat the random walk at all (MASE 1.032).

## 3. Sensitivity - was that a tuning artefact?

Same features, same snapshots, same origins; four configurations declared up front.

| h | default | regularised | heavy | linear leaves | AR(AIC) |
|---|---|---|---|---|---|
| 1 | 0.857 | 0.719 | **0.672** | 1.082 | 0.781 |
| 3 | 0.797 | 0.666 | **0.609** | 0.838 | 0.611 |
| 6 | 1.032 | 0.764 | **0.750** | 1.264 | 0.661 |
| 12 | 0.788 | **0.700** | 0.708 | 0.789 | 0.577 |

Diebold-Mariano against AR(AIC), Newey-West variance with lag h-1:

| h | best ML config | ML MASE | AR MASE | DM statistic | p | verdict |
|---|---|---|---|---|---|---|
| 1 | heavy | 0.672 | 0.781 | -1.96 | 0.050 | ML better (borderline) |
| 3 | heavy | 0.609 | 0.611 | -0.75 | 0.453 | no difference |
| 6 | heavy | 0.750 | 0.661 | +0.34 | 0.738 | no difference |
| 12 | heavy | 0.708 | 0.577 | +2.44 | 0.015 | **AR better** |

**Honest caveat, stated before anyone asks:** the "heavy" configuration was picked per horizon by looking at these very scores, so the h=1 win (p=0.050, exactly at the boundary) is optimistically biased. That caveat was tested in section 7 - and it was correct. Until then, the defensible claim was narrower:

> At horizon 1 a heavily regularised gradient-boosted model may edge a univariate AR; at horizons 3 and 6 the two are statistically indistinguishable; by horizon 12 the parsimonious AR is significantly better. With 66-77 overlapping origins, most of the gap other models advertise on Malaysian macro data sits inside the noise floor.

## 4. What leakage would have bought (measured, not asserted)

Identical LightGBM, features read with **no** publication lag:

| h | honest MASE | leaky MASE | improvement |
|---|---|---|---|
| 1 | 0.857 | 0.753 | 12% |
| 3 | 0.797 | 0.774 | 3% |
| 6 | 1.032 | 0.939 | 9% |
| 12 | 0.788 | 0.699 | 11% |

Useful number to have in an interview: leakage here is worth roughly a tenth of the error, not an order of magnitude - because exchange-rate and trade data arrive only 1 month behind the origin. The reason to enforce the mask is not that it flatters the model, it is that the flattery is unearned and undetectable from the score alone.

## 5. What this changes about the project

1. **AR(AIC) is the benchmark to beat, not the random walk.** RW MASE 1.0 is a low bar; AR clears it by 20-40%. Any ML claim must be against AR.
2. **Long horizons belong to parsimony.** The h=12 result is not noise (p=0.015). Do not fight it with more features - fight it with better uncertainty quantification.
3. **The interval work is now the main event, not a bonus.** If point forecasts cannot be separated at h=3-6, the deliverable that still adds value is calibrated prediction intervals and regime labels.
4. **Nested hyperparameter selection is a prerequisite**, not a refinement, before any "ML beats AR" line goes in the report or the app.

## 6. Next experiments, in priority order

1. Nested selection (inner window chooses config, outer window scores once) - settles the h=1 claim.
2. Probabilistic forecasts: quantile LightGBM + conformal intervals; check whether 80% intervals actually cover 80%.
3. AR-X / VAR comparison: does adding exports and OPR to the AR remove the ML's residual advantage at h=1?
4. Regime model on variance, not mean (Markov-switching on the AR residuals), since the mean dynamics look stable but the variance does not.

---

## 7. Nested selection - the claim that survives honest tuning

`scripts/nested_select.py`. Inside every outer training window the most recent 12 pairs are
held out, all four configurations are scored on them, and only the winner is refit and used.
The outer test target is never consulted. Origins require 36+12 training pairs, so the sample
is slightly smaller than in section 2 (65/63/60/54 instead of 77/75/72/66) - compare within
this table, not across tables.

| h | n | AR(AIC) | LightGBM nested | LightGBM heavy (fixed) | LightGBM default | nested vs AR (DM) |
|---|---|---|---|---|---|---|
| 1 | 65 | **0.753** | 0.775 | 0.723 | 0.908 | +0.19, p=0.853, no difference |
| 3 | 63 | **0.555** | 0.673 | 0.623 | 0.827 | +0.47, p=0.638, no difference |
| 6 | 60 | **0.575** | 0.790 | 0.814 | 1.085 | +1.49, p=0.136, no difference |
| 12 | 54 | **0.500** | 0.708 | 0.719 | 0.683 | +2.27, p=0.023, AR better |

The inner loop chose "heavy" in 41/65 origins at h=1, 36/63 at h=3, 34/60 at h=6, 30/54 at h=12 -
so it was not defaulting to one config out of laziness; it genuinely preferred the regularised
one and still lost to AR.

**Verdict, and it is the uncomfortable one:** once hyperparameter selection is done honestly,
LightGBM does not beat a univariate AR at any horizon, and at h=12 the AR is significantly
better. The earlier h=1 "ML win" (p=0.050) was selection bias, not skill - now demonstrated
rather than asserted. The `heavy (fixed)` column shows how large that bias is: it looks better
than the nested model that was supposed to pick it.

This is the finding to put in the report, in these words: *on 140 months of Malaysian data,
with publication lags respected, an AR(AIC) is the strongest point forecaster available, and
the ML models' apparent gains do not survive honest selection.* It is defensible, it is
reproducible from the repository, and it is worth more than a manufactured win.
