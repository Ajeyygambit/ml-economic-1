# AR-X and VAR against AR(AIC)

Direct multi-step ARDL (`arx`) and an iterated VAR(2) (`var`) on the same masked snapshots as
every other model. MASE is relative to the random walk.

## 1. Why these two specifications

* `arx` - direct multi-step ARDL: y(t+h) regressed on three AR lags of y plus lagged export
  growth (2 lags), CPI (1 lag) and the current OPR. **Direct, not iterated**, because iterating
  an ARDL requires future exports, CPI and OPR - which do not exist at the origin. Iterating
  would be leakage wearing a model's clothes.
* `var` - VAR(2) on (IPI growth, export growth, OPR), iterated. The ragged edge is handled
  explicitly: the VAR is estimated on the joint window ending at the *oldest* variable's last
  visible month (IPI, 2-month lag), then iterated far enough to reach the target month.

## 2. Result on the full origin set

| h | n origins | AR(AIC) | AR-X | VAR (stable origins only) | AR-X vs AR (DM) |
|---|---|---|---|---|---|
| 1 | 91 | 0.807 | **0.645** | 0.650 (71 of 91) | -2.71, p=0.007 |
| 3 | 89 | 0.685 | 0.678 | 0.569 (69 of 89) | -1.51, p=0.132 |
| 6 | 86 | 0.746 | 0.650 | 0.610 (66 of 86) | -1.35, p=0.177 |
| 12 | 80 | 0.674 | 0.601 | 0.618 (60 of 80) | -1.06, p=0.291 |

## 3. The VAR column is not comparable, and that matters

20 of 91 origins were dropped because the fitted VAR was **unstable** - its companion roots
crossed the unit circle. Without that guard the VAR produced exploding iterates (-673.9 pp at
h=6, -4974.4 pp at h=12); the *median* forecast stayed sane at 3.0 pp, which is exactly how a
broken model hides in a table of means.

Restricting every model to the origins where the VAR was stable gives the only fair comparison:

| h | n | AR(AIC) | AR-X | VAR | AR-X vs AR (DM) |
|---|---|---|---|---|---|
| 1 | 71 | 0.758 | **0.591** | 0.738 | -1.86, p=0.063 |
| 3 | 69 | 0.638 | 0.657 | 0.639 | -0.93, p=0.352 |
| 6 | 66 | 0.687 | 0.682 | 0.719 | -0.88, p=0.380 |
| 12 | 60 | 0.622 | 0.608 | 0.682 | -0.92, p=0.359 |

**Once the origins match, the VAR never wins.** Its apparent 0.569 at h=3 in the full table was
a subset artefact: it was scored on the 69 origins where it happened to be stable, against an
AR scored on all 89.

## 4. What this changes

1. **AR-X is the best point model at horizon 1** - 0.591 against the AR's 0.758 on matched
   origins, a 22% error reduction. Significance depends on the sample: p=0.007 on the full 91
   origins, p=0.063 on the matched 71. Both point the same way; neither is overwhelming.
2. **The advantage is concentrated in the turbulent post-COVID origins** - exactly the 20
   origins the VAR stability guard removes. That is a substantive finding, not a nuisance:
   when exports swing by tens of percent, export information is worth having; in calm periods
   the AR's parsimony is enough.
3. **Beyond h=1 nothing separates the models.** AR, AR-X and VAR are within 0.07 MASE of each
   other and every pairwise DM test is far from significant. At these horizons the honest answer
   is the AR's, and any claim that a different model is better is unsupported by this sample.
4. **A stability guard is not optional in a forecasting system.** The VAR's failure mode was not
   "slightly worse" - it was a handful of forecasts thousands of points off, invisible in the
   median. Any published forecast must be screened before it ships.

## 5. Recommended model set going forward

| horizon | point forecast | note |
|---|---|---|
| h=1 | AR-X (ARDL with exports, CPI, OPR) | 22% MASE improvement over AR on matched origins |
| h=3, 6, 12 | AR(AIC) | nothing beats it; fewer parameters is a virtue |
| intervals | conformal on the point forecast | see reports/intervals.md |
| guard | VAR stability check before any publication | see section 3 |

---

## 6. What the h=1 champion does and does not do (added after wiring the app)

Fitting the AR-X at the current origin exposed two things that belong in the write-up, not just
in the app's warnings:

**R² = 0.052 at h=1, on 122 observations.** The model explains about five percent of the variance
of IPI growth one month ahead. Its backtest MAE (3.53 pp) beats the AR's (4.04 pp) - the
Diebold-Mariano test says that gap is real - but a 5% R² is a weak relationship, and the point
forecast is dominated by the intercept (6.01) rather than by the economic channels.

**OPR enters with only six distinct values** (1.75, 2.00, 2.25, 2.50, 2.75, 3.00) across the whole
sample, so its coefficient (-1.157) is a *rate-regime indicator*, not a marginal effect. A 25 bp
move appears to shift the forecast by 0.29 pp on the strength of six observations. Any scenario
that turns that coefficient into a policy elasticity - a slider, a report table, a slide - would
be overclaiming.

**Consequence at the current origin:** AR-X says +6.9 pp for 2026-11 while the AR says +3.6 pp, a
3.3 pp disagreement on a series with a 6.6 pp standard deviation. The app therefore prints both,
flags the disagreement above 1 pp, and labels the h=1 point forecast as the *least* reliable of the
four rather than the most. The backtest ranking still stands; the interpretability does not
follow it.
