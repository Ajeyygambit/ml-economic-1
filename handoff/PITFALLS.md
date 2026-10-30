# PITFALLS - thirteen things that cost real time, so they do not cost yours

Each one was hit in the original build. They are ordered roughly by how much damage they do.

## 1. `python -m venv .venv` on a machine whose default Python is 3.14

Symptom: the venv is created, packages install, then

```
ImportError: Unable to import required dependency numpy
```

Cause: the interpreter version and the installed wheels disagree. Fix: build with Python 3.11.

```bash
uv venv .venv --python 3.11
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

## 2. Using the same-month value as a feature

The single most common leak in macro forecasting: forecasting month `m` while feeding the model
month `m`'s own industrial production, which is published in month `m+2`. Enforce the lag table in
exactly one function; if the logic is duplicated across notebooks, it will drift.

## 3. Hyperparameter selection on the test scores

Choosing a configuration by comparing out-of-sample results, then reporting the winner, inflated
one horizon's result from a loss to an apparent 22% win. Nested selection removed it entirely.
Cost of getting this wrong: the headline claim of the project.

## 4. Trade values arrive in ringgit, not millions

`api.data.gov.my` returns trade levels in ringgit (215,112,665,290), not RM million. Verify against
a known release: 2015-01 exports should be RM 62.97 billion. If your column says "millions" and the
value is 2.1e11, the label is wrong.

## 5. The API returns stacked series in one row set

`id=ipi` returns `series` values `abs`, `growth_mom`, `growth_yoy` in the same table. Filter by
`series` before pivoting, or you will silently mix an index level with a growth rate.
Same pattern for `trade_headline` (`abs`, `growth_mom`, `growth_yoy`) and `interestrates`
(`bank` x `rate` codes).

## 6. IPI starts at 2015 only

The index is rebased 2015=100, so the API's `ipi` series begins 2015-01. `ipi_growth_yoy` therefore
begins 2016-01 (it needs a year of base). At h=12 the effective training set is ~54 origin pairs -
that is the real bound on what any model here can claim.

## 7. Core CPI starts 2019, not 2015

`cpi_core_inflation` begins 2018-02. Either shorten the sample or treat it as an optional block
that is missing for the first four years.

## 8. The ragged edge is real, and different per series

As of the 2026-10 vintage: CPI and trade reach 2026-09, IPI/PPI/labour 2026-08, DOSM leading index
2026-07, interest rates and M2 2026-06, GDP 2026Q2. Any model that assumes a common last
observation is wrong.

## 9. OPR is not in the DOSM API

`interestrates` carries bank retail rates (BLR, FDR) only. BNM's Open API returns solely the latest
decision. The history has to be scraped from
`https://www.bnm.gov.my/monetary-stability/opr-decisions/-/tag/opr-YYYY` per year.

Two traps in that scrape:
- BNM's WAF returns **403 intermittently** - retry with backoff, realistic headers, and a delay.
- A missing year silently shifts the whole stepped series (an absent cut looks like the old rate
  persisting). **Refuse to publish** a stepped series if any year from 2015 onward failed.

Validate against known policy levels: 2020-05 = 2.00, 2020-07 = 1.75, 2022-05 = 2.00,
2023-05 = 3.00, 2025-07 = 2.75.

## 10. A level VAR on these three series explodes

`VAR(2)` on (target, export growth, OPR) produced iterates of -673.9 pp at h=6 and -4974.4 pp at
h=12, while the **median** forecast stayed near 3.0 pp - so the mean error looked catastrophic and
the median looked fine. 20 of 91 origins were affected.

Fix: check the companion roots (statsmodels' convention: stable when every |root| > 1) and refuse
to issue an unstable forecast. Then compare models only on the origins where all of them were
available - the VAR's apparently excellent MASE of 0.569 was a subset artefact.

## 11. Markov-switching converges to a degenerate state on a raw series

Fitting `MarkovRegression(switching_variance=True)` to the unstandardised target produced a state
with variance ~1e5 and probability ~0, which labelled every month "calm" - a clean-looking result
that was entirely an artefact.

Fix: standardise inside each expanding window using that window's own mean and standard deviation.
Also note `filtered_marginal_probabilities` has shape **(n_obs, k_regimes)**, so the current state
is `probs[-1, high_variance_state]`, not `probs[state, -1]`.

## 12. Quantile GBM intervals are too narrow

Three quantile LightGBM models (5/10/90/95) delivered 0.64 coverage at a nominal 0.80 - trees
regress toward the conditional mean and the intervals collapse. Conformal intervals built from
past errors over-cover instead (0.88-0.93) but win on pinball loss. Measure coverage; do not
assume.

## 13. Small traps

- `pandas.DataFrame.to_markdown` needs `tabulate` installed.
- `df.var` and `df.ar` are DataFrame/Series **methods** - attribute access silently returns a
  function. Use `df["var"]`. This produced a `TypeError: unsupported operand type(s) for -: 'method' and 'float'`.
- `statsmodels` `add_constant` on a DataFrame returns a Series index-preserving object; index with
  `np.asarray(...)[0]`, not `[0]`.
- The DOSM API redirects to a trailing-slash URL: `curl` needs `-L` or you get an empty body with
  HTTP 301.
