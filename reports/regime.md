# Volatility regimes and their effect on forecast error

Two-state Markov-switching AR with state-dependent variance, fitted on an expanding window (60+ months before the first label). 69 months labelled, 14.5% of them in the turbulent state.

The regime label uses only data available at that month, so it is a real-time label, not a full-sample smoother that a backtest could not have had.

## Error and interval coverage by regime

|   h |   n_calm |   err_calm |   cov80_calm |   width_calm |   n_turbulent |   err_turbulent |   cov80_turbulent |   width_turbulent |   mwu_p |
|----:|---------:|-----------:|-------------:|-------------:|--------------:|----------------:|------------------:|------------------:|--------:|
|   1 |       54 |       3.23 |        1     |        15.06 |            10 |            7.84 |                 1 |             26.98 |   0.006 |
|   3 |       52 |       2.41 |        0.981 |        11.38 |            10 |            3.62 |                 1 |             14.19 |   0.114 |
|   6 |       49 |       2.64 |        1     |        14.35 |            10 |            1.59 |                 1 |             16.09 |   0.088 |
|  12 |       44 |       1.96 |        1     |        15.14 |            10 |            4.54 |                 1 |             16.93 |   0.002 |

`calm_vs_turbulent_p` is a Mann-Whitney test on the absolute AR errors of the two states.

## Why this matters more than the point forecast

If nominal-80% conformal intervals cover roughly 80% in the calm state and materially
less in the turbulent state, then a single fixed-width interval is mis-specified by
construction, and the fix is a regime-conditional width - which is a defensible,
testable design choice rather than a modelling flourish.
## Result

Two-state Markov-switching AR with state-dependent variance, standardised inside each expanding
window (fitting the raw series converged to a degenerate state with variance ~1e5 and probability
~0, which silently made the regime vacuous - a failure worth recording because it looks like a
clean result). 69 months labelled as of the current vintage, **10 of them turbulent**, all of them
in the 2020-2021 and 2026 coverage windows.

| h | calm: n / mean AR error | turbulent: n / mean AR error | Mann-Whitney p | 80% conformal width calm vs turbulent |
|---|---|---|---|---|
| 1 | 54 / 3.23 pp | 10 / 7.84 pp | **0.006** | 15.06 vs 26.98 pp |
| 3 | 52 / 2.41 pp | 10 / 3.62 pp | 0.114 | 11.38 vs 14.19 pp |
| 6 | 49 / 2.64 pp | 10 / 1.59 pp | 0.088 | 14.35 vs 16.09 pp |
| 12 | 44 / 1.96 pp | 10 / 4.54 pp | **0.002** | 15.14 vs 16.93 pp |

## What this says, and what it does not

* **Error is 2.4x larger in the turbulent state at h=1** (3.23 -> 7.84 pp, p=0.006) and 2.3x
  larger at h=12 (1.96 -> 4.54 pp, p=0.002). The regime label carries real information about
  how wrong a forecast will be.
* **The effect is not monotone.** At h=6 the turbulent state actually shows a *lower* mean error
  (1.59 vs 2.64 pp). With only 10 turbulent origins, that is not evidence of anything - and
  reporting only the two significant horizons would be cherry-picking. The honest statement is:
  the signal is strongest at the shortest and longest horizons and absent in the middle.
* **The fixed-width interval did not fail.** Coverage stayed at 1.000 in both states, because the
  conformal interval is sized from *past* errors, which widen automatically after a turbulent
  stretch (15.06 -> 26.98 pp at h=1). The mechanism worked without a regime input.
* **Therefore the regime is not needed to fix the intervals** - it is needed to explain them.
  The production value is a published label ("you are currently in the turbulent state, expect
  roughly twice the usual error"), not an extra parameter inside the interval.

## Limitation

Ten turbulent origins is a very small cell. The regime label is useful as a communication device
and as a diagnostic, but it cannot be used as a modelling input with this sample: any coefficient
estimated on ten observations would be fitting noise.
