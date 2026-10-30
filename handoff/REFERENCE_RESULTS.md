# REFERENCE RESULTS - sanity anchors from the original build

The numbers below were produced by the first implementation, on this exact vintage, with the
mask enforced and expanding-window rolling origins. Use them to check that your rebuild is in
the same universe - **not as targets to beat**.

Panel: 142 months, 33 columns, 2015-01 to 2026-10.
Random walk MASE is 1.000 by construction.

## 1. Point forecasts - nested (honest) selection, n=65/63/60/54

|   h |   origins |   AR(AIC) |   LightGBM nested |   LightGBM heavy (post-hoc, biased) |   DM p vs AR |
|----:|----------:|----------:|------------------:|------------------------------------:|-------------:|
|   1 |        65 |     0.753 |             0.775 |                               0.723 |        0.853 |
|   3 |        63 |     0.555 |             0.673 |                               0.623 |        0.638 |
|   6 |        60 |     0.575 |             0.79  |                               0.814 |        0.136 |
|  12 |        54 |     0.5   |             0.708 |                               0.719 |        0.023 |

Reading: at every horizon the honest ML pipeline sits above the AR. The `heavy_fixed` column shows
how much a post-hoc choice would have flattered it (0.723 at h=1 versus the nested 0.775).

## 2. AR-X and VAR - matched origins only, n=71/69/66/60

|   h |   origins |   AR(AIC) |   AR MAE |   AR-X |   AR-X MAE |   VAR |   VAR MAE |
|----:|----------:|----------:|---------:|-------:|-----------:|------:|----------:|
|   1 |        71 |     0.758 |     3.65 |  0.591 |       2.85 | 0.738 |      3.55 |
|   3 |        69 |     0.638 |     3.35 |  0.657 |       3.45 | 0.639 |      3.36 |
|   6 |        66 |     0.687 |     3.36 |  0.682 |       3.33 | 0.719 |      3.52 |
|  12 |        60 |     0.622 |     3.63 |  0.608 |       3.54 | 0.682 |      3.98 |

Reading: AR-X wins at h=1 (0.591 vs 0.758). Beyond h=1 nothing separates the three.

## 3. VAR stability guard - how often it fired

|   h |   n_origins |   var_origins_stable |   var_origins_skipped_unstable |
|----:|------------:|---------------------:|-------------------------------:|
|   1 |          91 |                   71 |                             20 |
|   3 |          89 |                   69 |                             20 |
|   6 |          86 |                   66 |                             20 |
|  12 |          80 |                   60 |                             20 |

Without the guard, VAR MASE reached 12.652 at h=12 with forecasts down to -4974 pp.

## 4. Interval calibration

|   h |   n_origins |   AR normal 80% |   quantile LGBM 80% |   conformal 80% |   AR normal 95% |   quantile LGBM 95% |   conformal 95% |
|----:|------------:|----------------:|--------------------:|----------------:|----------------:|--------------------:|----------------:|
|   1 |          77 |           0.87  |               0.636 |           0.923 |           0.922 |               0.883 |           0.985 |
|   3 |          75 |           0.92  |               0.64  |           0.921 |           0.96  |               0.88  |           0.984 |
|   6 |          72 |           0.917 |               0.639 |           0.883 |           0.931 |               0.903 |           1     |
|  12 |          66 |           0.955 |               0.636 |           0.926 |           0.955 |               0.955 |           1     |

Nominal is 0.80 / 0.95. Quantile GBM under-covers; conformal and AR-normal over-cover.

Mean 80% interval widths (pp): h=1: AR normal 18.0, quantile 5.7, conformal 16.9, h=3: AR normal 18.1, quantile 5.9, conformal 11.8, h=6: AR normal 18.3, quantile 6.4, conformal 14.6, h=12: AR normal 18.5, quantile 7.0, conformal 15.5.

## 5. Volatility regimes

|   h |   n_calm |   err_calm |   cov80_calm |   width_calm |   n_turbulent |   err_turbulent |   cov80_turbulent |   width_turbulent |   mwu_p |
|----:|---------:|-----------:|-------------:|-------------:|--------------:|----------------:|------------------:|------------------:|--------:|
|   1 |       54 |       3.23 |        1     |        15.06 |            10 |            7.84 |                 1 |             26.98 |   0.006 |
|   3 |       52 |       2.41 |        0.981 |        11.38 |            10 |            3.62 |                 1 |             14.19 |   0.114 |
|   6 |       49 |       2.64 |        1     |        14.35 |            10 |            1.59 |                 1 |             16.09 |   0.088 |
|  12 |       44 |       1.96 |        1     |        15.14 |            10 |            4.54 |                 1 |             16.93 |   0.002 |

69 months labelled, 10 turbulent. Error is 2.4x larger in turbulence at h=1 (p=0.006) and 2.3x at
h=12 (p=0.002), but the direction reverses at h=6 (p=0.088) - report that, do not cherry-pick.

## 6. LightGBM configuration sensitivity (post-hoc, for reference only)

|   h |   n_origins |   rw_MASE |   default_MASE |   default_MAE |   regularised_MASE |   regularised_MAE |   heavy_MASE |   heavy_MAE |   linear_leaves_MASE |   linear_leaves_MAE |
|----:|------------:|----------:|---------------:|--------------:|-------------------:|------------------:|-------------:|------------:|---------------------:|--------------------:|
|   1 |          77 |         1 |          0.87  |         5.393 |              0.719 |             4.461 |        0.672 |       4.168 |                1.082 |               6.711 |
|   3 |          75 |         1 |          0.802 |         4.769 |              0.666 |             3.959 |        0.609 |       3.621 |                0.838 |               4.981 |
|   6 |          72 |         1 |          1.059 |         6.1   |              0.764 |             4.401 |        0.75  |       4.319 |                1.264 |               7.279 |
|  12 |          66 |         1 |          0.775 |         4.989 |              0.7   |             4.502 |        0.708 |       4.554 |                0.789 |               5.075 |

## How to use these anchors

| if your result is | then |
|---|---|
| within about +/-10% MASE of these | plausible, proceed |
| much worse | check the mask, the origin count, and whether features are NaN at the edges |
| much better | **assume leakage** and find it before reporting. Check: same-month values, scalers fitted on the full sample, hyperparameters chosen on test scores, overlapping training rows that include the target month |
