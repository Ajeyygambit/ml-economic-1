# Probabilistic forecasts - calibration audit

Target `ipi_growth_yoy`, rolling origins, publication-lag mask enforced.
Nominal coverage is what the interval promises; empirical is what it delivered.

## h = 1 (n = 77.0 origins, 65.0 after the conformal warm-up)

Point MASE - AR 0.781, LightGBM 0.672.

| method            |   nominal |   empirical |    gap |   mean width (pp) |   pinball |
|:------------------|----------:|------------:|-------:|------------------:|----------:|
| ar_normal_80      |      0.8  |       0.87  |  0.07  |             18.03 |     3.6   |
| lgbm_quantile_80  |      0.8  |       0.636 | -0.164 |              5.71 |     2.82  |
| lgbm_conformal_80 |      0.8  |       0.923 |  0.123 |             16.86 |     2.448 |
| ar_conformal_80   |      0.8  |       0.969 |  0.169 |             24.58 |     2.945 |
| ar_normal_95      |      0.95 |       0.922 | -0.028 |             27.57 |     2.2   |
| lgbm_quantile_95  |      0.95 |       0.883 | -0.067 |             22.56 |     2.025 |
| lgbm_conformal_95 |      0.95 |       0.985 |  0.035 |             51.79 |     1.593 |
| ar_conformal_95   |      0.95 |       0.985 |  0.035 |             54.24 |     1.635 |

## h = 3 (n = 75.0 origins, 63.0 after the conformal warm-up)

Point MASE - AR 0.611, LightGBM 0.609.

| method            |   nominal |   empirical |    gap |   mean width (pp) |   pinball |
|:------------------|----------:|------------:|-------:|------------------:|----------:|
| ar_normal_80      |      0.8  |       0.92  |  0.12  |             18.14 |     2.703 |
| lgbm_quantile_80  |      0.8  |       0.64  | -0.16  |              5.91 |     2.148 |
| lgbm_conformal_80 |      0.8  |       0.921 |  0.121 |             11.79 |     1.32  |
| ar_conformal_80   |      0.8  |       0.921 |  0.121 |             14.16 |     1.53  |
| ar_normal_95      |      0.95 |       0.96  |  0.01  |             27.75 |     1.393 |
| lgbm_quantile_95  |      0.95 |       0.88  | -0.07  |             22.4  |     1.535 |
| lgbm_conformal_95 |      0.95 |       0.984 |  0.034 |             28.22 |     0.709 |
| ar_conformal_95   |      0.95 |       1     |  0.05  |             35.1  |     0.877 |

## h = 6 (n = 72.0 origins, 60.0 after the conformal warm-up)

Point MASE - AR 0.661, LightGBM 0.75.

| method            |   nominal |   empirical |    gap |   mean width (pp) |   pinball |
|:------------------|----------:|------------:|-------:|------------------:|----------:|
| ar_normal_80      |      0.8  |       0.917 |  0.117 |             18.33 |     2.755 |
| lgbm_quantile_80  |      0.8  |       0.639 | -0.161 |              6.41 |     2.343 |
| lgbm_conformal_80 |      0.8  |       0.883 |  0.083 |             14.61 |     1.578 |
| ar_conformal_80   |      0.8  |       0.95  |  0.15  |             14.83 |     1.57  |
| ar_normal_95      |      0.95 |       0.931 | -0.019 |             28.03 |     1.414 |
| lgbm_quantile_95  |      0.95 |       0.903 | -0.047 |             25.03 |     1.66  |
| lgbm_conformal_95 |      0.95 |       1     |  0.05  |             30.11 |     0.753 |
| ar_conformal_95   |      0.95 |       1     |  0.05  |             33.64 |     0.841 |

## h = 12 (n = 66.0 origins, 54.0 after the conformal warm-up)

Point MASE - AR 0.577, LightGBM 0.708.

| method            |   nominal |   empirical |    gap |   mean width (pp) |   pinball |
|:------------------|----------:|------------:|-------:|------------------:|----------:|
| ar_normal_80      |      0.8  |       0.955 |  0.155 |             18.47 |     2.908 |
| lgbm_quantile_80  |      0.8  |       0.636 | -0.164 |              7.02 |     2.575 |
| lgbm_conformal_80 |      0.8  |       0.926 |  0.126 |             15.47 |     1.649 |
| ar_conformal_80   |      0.8  |       0.907 |  0.107 |             13.3  |     1.433 |
| ar_normal_95      |      0.95 |       0.955 |  0.005 |             28.25 |     1.717 |
| lgbm_quantile_95  |      0.95 |       0.955 |  0.005 |             27.45 |     1.617 |
| lgbm_conformal_95 |      0.95 |       1     |  0.05  |             32.15 |     0.804 |
| ar_conformal_95   |      0.95 |       1     |  0.05  |             31.71 |     0.793 |

## How to read this

- A method is calibrated when empirical coverage lands near nominal. Over-coverage means the interval is too wide to be useful; under-coverage means it lies.
- Pinball loss rewards sharpness subject to calibration, so it is the tie-breaker between two methods that are both roughly calibrated.
- Conformal intervals warm up: the first 12 origins have no interval because there was no error history to size them from. That is a feature, not a gap.
## What this actually says

**1. Every 80% interval is mis-sized, in opposite directions.** Quantile LightGBM under-covers
badly (0.636-0.640 against a nominal 0.80): the trees regress to the conditional mean and
produce intervals that are too tight. The conformal variants and the AR's own normal interval
over-cover (0.87-0.97). Nothing lands on 0.80 at every horizon.

**2. The sample cannot settle it.** With 54-65 scored origins, the standard error on a coverage
estimate near 0.80 is roughly 5 percentage points. An observed 0.88 is therefore *not*
distinguishable from 0.80. Saying "the intervals are calibrated" would be overclaiming; saying
"they are wrong" would also be overclaiming. The honest statement is that this sample cannot
verify calibration to better than about +/-5 pp, which is exactly why the intervals that ship
must be conservative.

**3. The width is the finding that matters.** An 80% interval for one-month-ahead IPI growth is
11-17 pp wide, against a series whose mean is 3.5% and whose standard deviation is 6.6 pp. The
interval covers most of the plausible range of the series. That is the real answer to "how
confident should decision-makers be": not very - and here is the arithmetic rather than a
sentence about uncertainty.

**4. Pinball loss prefers the conformal approach.** At both nominal levels the residual-quantile
(conformal) intervals score better than the quantile-GBM intervals despite being wider, because
they are centred on the point forecast rather than pushed around by an unstable quantile fit.
That is the method to ship - with the width stated plainly next to every forecast.
