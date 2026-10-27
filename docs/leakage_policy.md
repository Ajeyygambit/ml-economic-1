# Leakage Policy - ML Economic 1 (Ajey)

**Status:** enforced in code, not just in prose.
**Enforcement point:** `scripts/build_publication_lag.py` produces `data/publication_lag.csv`;
`scripts/check_availability.py` proves the mask holds before any model is trained.
**Reference month in this document:** `T` = the month in which the forecast is made
(the "origin"), taken as *known at the end of T*.

---

## 1. The one rule

> At the end of month `T`, a forecaster may use series `s` only up to month
> `T - lag(s)`, where `lag(s)` is that series' publication lag.

Every other rule in this document is a corollary. The mask is applied in exactly one
function (`available_asof` in `scripts/check_availability.py`) so it cannot drift
between notebooks, the app and the report.

## 2. The lag table (measured, not assumed)

`lag_months` is established two ways and the larger of the two is used:

* **observed** - how many months behind the current month the official API's newest
  observation is today;
* **documented** - the agency's stated release practice.

| lag | series | why |
|---|---|---|
| 0 | `opr`, `opr_changed_in_month` | MPC decision issued at 3 p.m. on decision day - same-day public |
| 1 | `cpi_*`, `exports_*`, `imports_*`, `trade_balance_rm_mil`, `myr_per_usd` | CPI 3-4 weeks, trade 4-5 weeks; monthly FX mean only completes at month end |
| 2 | `ipi_*`, `ppi_growth_yoy`, `u_rate`, `p_rate`, `lf_employed` | IPI/PPI ~2 months; LFS monthly ~5-6 weeks |
| 3 | `li_leading`, `li_coincident`, `li_lagging`, `li_leading_diffusion` | DOSM Malaysian Economic Indicators |
| 4 | `blr`, `fdr_1mo`, `fdr_3mo`, `m2_rm_mil`, `m3_rm_mil` | BNM monthly banking/monetary statistics |

Full machine-readable version: `data/publication_lag.csv`.

**Consequence for the headline target.** If `T = 2026-10`, the newest usable IPI is
`2026-08`. A 1-month-ahead forecast is therefore a forecast of `2026-11` - three months
past the newest observation. That is the real task, and phrasing it honestly is worth
more in an interview than a tight RMSE obtained by cheating.

## 3. Six ways this project could leak, and how each is blocked

| # | Leak | Block |
|---|---|---|
| 1 | **Publication lag** - using IPI for month `m` when forecasting `m`, though it appears in month `m+2` | `available_asof` truncation per `lag_months` |
| 2 | **Revision / vintage** - using a 2026 revision of 2015 data and pretending it was known in 2015 | Not fully solvable (Malaysia has no public real-time database). Mitigation below. |
| 3 | **Target contamination** - target = `ipi_growth_yoy(t+h)` while a feature is `ipi_index(t+h)` | Target and features are built from the same masked frame; no column may exceed its own cutoff |
| 4 | **Partial-period average** - "current month" FX average or month-to-date trade | `myr_per_usd` lagged to 1; nothing month-to-date enters |
| 5 | **Full-sample scaling** - standardising with a mean/std computed over the test period | All scalers fitted inside each rolling origin, on training rows only |
| 6 | **Tuning on the test set** - choosing hyperparameters by looking at out-of-sample scores across the whole history | Hyperparameters chosen on an inner validation window; the outer rolling-origin scores are touched once, at the end |

## 4. What is *not* solved: revisions

Malaysia publishes revised GDP, IPI and trade figures, and there is no public ALFRED-style
vintage archive. So this project's honest claim is:

> Results are computed on a **fixed vintage** (the download dated in `data/manifest.json`),
> with publication lags respected but revisions ignored. Revision error is therefore an
> unquantified extra source of error, expected to be small for IPI growth and larger for
> quarterly GDP levels.

Two mitigations, both cheap and both reportable:

1. **Freeze the vintage.** Every run writes `manifest.json` with timestamps, so a result
   can be reproduced against the exact same snapshot.
2. **Revision sensitivity band.** Re-run the final backtest with targets perturbed
   +/- 0.3 pp (a plausible revision size for IPI yoy). If the model ranking does not
   change, say so - that is evidence. If it does, that is a finding, not a failure.

## 5. Pre-build checklist (run before every backtest, app refresh and report)

```bash
python scripts/fetch_data.py            # refresh raw + panel
python scripts/fetch_opr.py             # refresh OPR history (BNM)
python scripts/build_publication_lag.py # rebuild the lag table from live data
python scripts/check_availability.py    # must print PASS
```

If `check_availability.py` prints `LEAK` or exits non-zero, the feature matrix is
contaminated and any score produced after it is fiction. As of the current vintage it
reports: 51 observations that a leaky build would have used at origin `2026-08`, all
correctly withheld.

## 6. Reporting contract

Any table of results in the report or the app must state, in the same block:

* forecast origin range and the number of rolling origins;
* the horizon(s), and the newest observation each horizon was allowed to see;
* the vintage date of the download;
* whether the baseline beat the ML model (report it either way).

A backtest number without those four lines will not be trusted by a reviewer - and should
not be.
