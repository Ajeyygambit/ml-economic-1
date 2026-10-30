# ML Economic 1 (Ajey) - Data Dictionary

**Generated:** 2026-10-26  
**Panel:** `data/panel_monthly.csv` - 141 months, 2015-01 to 2026-09, 31 series  
**Quarterly:** `data/panel_quarterly.csv` - 46 quarters, 2015-01-01 to 2026-04-01  
**Pipeline:** `scripts/fetch_data.py` (stdlib only, re-runnable, every URL logged in `data/manifest.json`)

## 1. Sources (all official, no third-party scrapers)

Every series comes from `https://api.data.gov.my/data-catalogue` - the official open-data API
operated by DOSM/MAMPU - except the OPR, which is not exposed there (see section 4).

| catalogue | API id | raw rows | first | last | raw file |
|---|---|---|---|---|---|
| ipi | `?id=ipi` | 407 | 2015-01-01 | 2026-08-01 | `data/raw/ipi.csv` |
| ipi_1d | `?id=ipi_1d` | 1221 | 2015-01-01 | 2026-08-01 | `data/raw/ipi_1d.csv` |
| cpi_headline_inflation | `?id=cpi_headline_inflation` | 7840 | 1980-02-01 | 2026-09-01 | `data/raw/cpi_headline_inflation.csv` |
| cpi_core_inflation | `?id=cpi_core_inflation` | 1456 | 2018-02-01 | 2026-09-01 | `data/raw/cpi_core_inflation.csv` |
| lfs_month_sa | `?id=lfs_month_sa` | 200 | 2010-01-01 | 2026-08-01 | `data/raw/lfs_month_sa.csv` |
| trade_headline | `?id=trade_headline` | 1310 | 1990-01-01 | 2026-09-01 | `data/raw/trade_headline.csv` |
| exchangerates | `?id=exchangerates` | 1785 | 1997-01-01 | 2026-09-01 | `data/raw/exchangerates.csv` |
| interestrates | `?id=interestrates` | 5808 | 1997-01-01 | 2026-06-01 | `data/raw/interestrates.csv` |
| ppi | `?id=ppi` | 587 | 2010-01-01 | 2026-08-01 | `data/raw/ppi.csv` |
| monetary_aggregates | `?id=monetary_aggregates` | 1944 | 2013-01-01 | 2026-06-01 | `data/raw/monetary_aggregates.csv` |
| economic_indicators | `?id=economic_indicators` | 427 | 1991-01-01 | 2026-07-01 | `data/raw/economic_indicators.csv` |
| gdp_qtr_real_sa | `?id=gdp_qtr_real_sa` | 46 | 2015-01-01 | 2026-04-01 | `data/raw/gdp_qtr_real_sa.csv` |
| gdp_qtr_real | `?id=gdp_qtr_real` | 133 | 2015-01-01 | 2026-04-01 | `data/raw/gdp_qtr_real.csv` |

Raw downloads are kept verbatim per catalogue in `data/raw/`, so a later pipeline run can be
diffed against this vintage.

## 2. Monthly panel

| column | definition | unit | source catalogue | first obs | last obs | missing |
|---|---|---|---|---|---|---|
| `ipi_index` | Industrial Production Index, total, 2015=100, NSA | index | ipi | 2015-01 | 2026-08 | 1 |
| `ipi_index_sa` | Same index, seasonally adjusted by DOSM | index | ipi | 2015-01 | 2026-08 | 1 |
| `ipi_mining_index` | IPI, section B (mining) | index | ipi_1d | 2015-01 | 2026-08 | 1 |
| `ipi_manufacturing_index` | IPI, section C (manufacturing) | index | ipi_1d | 2015-01 | 2026-08 | 1 |
| `ipi_electricity_index` | IPI, section D (electricity) | index | ipi_1d | 2015-01 | 2026-08 | 1 |
| `cpi_inflation_yoy` | Headline CPI inflation, overall | % yoy | cpi_headline_inflation | 2015-01 | 2026-09 | 0 |
| `cpi_inflation_mom` | Headline CPI inflation, overall | % mom | cpi_headline_inflation | 2015-01 | 2026-09 | 0 |
| `cpi_div01_yoy` | CPI division 01 = food & non-alcoholic beverages | % yoy | cpi_headline_inflation | 2015-01 | 2026-09 | 0 |
| `cpi_div04_yoy` | CPI division 04 = housing, water, electricity, gas | % yoy | cpi_headline_inflation | 2015-01 | 2026-09 | 0 |
| `u_rate` | Unemployment rate, seasonally adjusted | % of labour force | lfs_month_sa | 2015-01 | 2026-08 | 1 |
| `p_rate` | Labour force participation rate, SA | % | lfs_month_sa | 2015-01 | 2026-08 | 1 |
| `lf_employed` | Employed persons, SA | thousand persons | lfs_month_sa | 2015-01 | 2026-08 | 1 |
| `exports_rm_mil` | Gross exports (converted from ringgit) | RM million | trade_headline | 2015-01 | 2026-09 | 0 |
| `imports_rm_mil` | Gross imports (converted) | RM million | trade_headline | 2015-01 | 2026-09 | 0 |
| `trade_balance_rm_mil` | Trade balance (converted) | RM million | trade_headline | 2015-01 | 2026-09 | 0 |
| `exports_growth_yoy` | Export growth | % yoy | trade_headline | 2015-01 | 2026-09 | 0 |
| `imports_growth_yoy` | Import growth | % yoy | trade_headline | 2015-01 | 2026-09 | 0 |
| `myr_per_usd` | Monthly mean of daily noon MYR/USD (BNM reference rate) | MYR per USD | exchangerates | 2015-01 | 2026-09 | 0 |
| `blr` | Base lending rate, commercial banks (weighted) | % pa | interestrates | 2015-01 | 2026-06 | 3 |
| `fdr_1mo` | Fixed deposit rate, 1-month, commercial banks (weighted) | % pa | interestrates | 2015-01 | 2026-06 | 3 |
| `fdr_3mo` | Fixed deposit rate, 3-month, commercial banks (weighted) | % pa | interestrates | 2015-01 | 2026-06 | 3 |
| `ppi_growth_yoy` | Producer Price Index, local production, growth | % yoy | ppi | 2015-01 | 2026-08 | 1 |
| `m2_rm_mil` | Broad money M2 | RM million | monetary_aggregates | 2015-01 | 2026-06 | 3 |
| `m3_rm_mil` | Broad money M3 | RM million | monetary_aggregates | 2015-01 | 2026-06 | 3 |
| `li_leading` | DOSM Leading Index | index 2015=100 | economic_indicators | 2015-01 | 2026-07 | 2 |
| `li_coincident` | DOSM Coincident Index | index 2015=100 | economic_indicators | 2015-01 | 2026-07 | 2 |
| `li_lagging` | DOSM Lagging Index | index 2015=100 | economic_indicators | 2015-01 | 2026-07 | 2 |
| `li_leading_diffusion` | Leading Index diffusion (% of components expanding) | % | economic_indicators | 2015-01 | 2026-07 | 2 |
| `ipi_growth_mom` | IPI month-on-month growth | % mom | ipi | 2015-02 | 2026-08 | 2 |
| `ipi_growth_yoy` | IPI year-on-year growth  <- PRIMARY TARGET candidate (h=1,3,6,12) | % yoy | ipi | 2016-01 | 2026-08 | 13 |
| `cpi_core_yoy` | Core CPI inflation (excludes volatile fresh food & administered prices) | % yoy | cpi_core_inflation | 2019-01 | 2026-09 | 48 |

Quarterly file (`panel_quarterly.csv`):

| column | definition | unit | source catalogue |
|---|---|---|---|
| `gdp_real_sa_rm_mil` | Real GDP, seasonally adjusted | RM million (2015 prices) | gdp_qtr_real_sa |
| `gdp_real_rm_mil` | Real GDP, NSA | RM million (2015 prices) | gdp_qtr_real |
| `gdp_growth_yoy` | Real GDP growth | % yoy | gdp_qtr_real |

## 3. The ragged edge is real and visible (do not smooth it away)

Data do **not** all end in the same month. Last observation per block as of this run:

- CPI, external trade -> **2026-09**
- IPI, PPI, labour force, DOSM indices -> **2026-08**
- Interest rates, M2/M3 -> **2026-06**
- Quarterly GDP -> **2026-Q2** (2026-04-01)

That is the publication-lag problem in miniature. A forecast for month `m` may only use what was
*actually published* by the forecast date - so the feature matrix needs a per-series availability
mask (see `docs/leakage_policy.md`, written in Week 1), not just lagged columns.

## 4. Known gaps and caveats

1. **OPR is missing from the panel.** `api.data.gov.my` carries bank retail rates (`interestrates`)
   but not the policy rate. BNM's Open API returns only the *latest* decision
   (`/public/opr` -> 2.75% effective 2026-09-03). Full OPR history must be scraped from
   `https://www.bnm.gov.my/monetary-stability/opr-decisions` (per-year views) and spliced in;
   until then `blr` / `fdr_1mo` / `fdr_3mo` act as monetary-condition proxies - and BLR adjusts with a lag.
2. **Core CPI starts 2019-01** in this catalogue, not 2015. Either shorten the sample or treat it as
   an optional block that is missing for the first 48 months.
3. **Revisions are not modelled.** These are latest-vintage series. Malaysia has no public
   real-time database equivalent to ALFRED, so the defensible approach is a publication-lag mask
   (pseudo-vintage), documented as an explicit limitation rather than pretending it is solved.
4. **Trade values arrive in ringgit**, not millions - the pipeline divides by 1e6. Verified:
   2015-01 exports = 62,971,395,081 = RM 62.97b, which matches the official release.
5. **CPI "overall" is not a division.** Checked: `overall` differs from division 01 in ~97% of
   months (mean absolute gap 1.44 pp), so the aggregate is genuinely separate and not a
   mis-mapped component.
6. **Export growth of +54.5% yoy in 2026-09 looks extreme** but is not a parsing error: the same
   month is byte-identical across two independent catalogues (`trade_headline` and
   `trade_sitc_1d`). Treat it as a genuine feature of the current boom - and watch it as a
   potential structural break in the regime model.
7. **`gdp_qtr_real_sa` publishes only the level (`abs`)**, no growth series; growth is computed from
   `gdp_qtr_real` (NSA) instead. Do not mix the SA and NSA levels - they differ by ~2%.

## 5. Verified checkpoints from this run

| check | result |
|---|---|
| Two catalogues agree on exports/imports levels | yes, 0.000% difference for 2026-04..09 |
| Exports unit conversion | 2015-01 = RM 62.97b (matches official release) |
| CPI aggregate vs component | overall != division 01 in 96.8% of months |
| Panel completeness | 141 months x 31 series, no duplicate months |
| BNM OPR live | 2.75% effective 2026-09-03 |

## 6. OPR columns (added after the first build)

| column | definition | unit | source |
|---|---|---|---|
| `opr` | Overnight Policy Rate in force at month end | % pa | BNM MPC decisions (`bnm.gov.my/monetary-stability/opr-decisions`, walked by year tag 2004-2026) |
| `opr_changed_in_month` | 1 if the MPC met and moved the rate that month | flag | same |

Coverage: 140 decisions from 2004-05-26 to 2026-09-03, expanded to a daily stepped series then
collapsed to monthly (270 months, of which 142 fall in the panel). Self-check in
`scripts/fetch_opr.py` validates six known policy levels (2020-05 = 2.00, 2020-07 = 1.75,
2022-05 = 2.00, 2023-05 = 3.00, 2025-07 = 2.75, 2026-09 = 2.75) - all pass.

**Fetching note:** BNM's WAF intermittently returns 403 on the year-tag pages. The script retries
with backoff and *refuses to publish* a stepped series if any year from 2015 onward is missing,
because an absent cut silently looks like the old rate persisting.

## 7. Publication lag (the mask)

`data/publication_lag.csv` carries `lag_months` per series, derived from the newest observation
each catalogue actually holds plus each agency's documented release practice. Enforced by
`scripts/check_availability.py`, which must print PASS before any model is trained.
At origin 2026-08 it withholds 51 observations that a leaky build would have used.
