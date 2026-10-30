# PROMPT - paste this to the other model

You are building a research-grade macroeconomic forecasting system for Malaysia. Work from the
data files in this folder. Do not invent data, do not invent results, and do not report a number
you did not compute.

## The task

Forecast **Malaysian industrial production growth (IPI, year-on-year, %)** at horizons of
**1, 3, 6 and 12 months**, and answer four questions with evidence:

1. Can it be forecast at all beyond a naive benchmark, and by how much?
2. Which predictors carry genuine out-of-sample signal, and which only look useful in-sample?
3. What does the shape of the uncertainty look like - are 80% and 95% intervals honest?
4. Does the state of the economy (calm vs turbulent volatility) change how wrong a forecast will be?

## Data you are given (do not replace it)

| file | contents |
|---|---|
| `data/panel_monthly.csv` | 142 months (2015-01 to 2026-10), 33 columns, the modelling panel |
| `data/publication_lag.csv` | `lag_months` per column - **mandatory**, see below |
| `data/opr_monthly.csv` | Overnight Policy Rate in force per month |
| `data/panel_quarterly.csv` | real GDP, 46 quarters |
| `data/DATA_DICTIONARY.md` | every column: definition, unit, source, coverage, caveats |
| `data/manifest.json` | source URL and fetch timestamp for each series |

The panel is real, downloaded from Malaysia's official open-data API and Bank Negara Malaysia.
Vintage: 2026-10-26. Treat it as fixed - do not fetch new data and mix vintages.

## Non-negotiable rules

1. **Publication lags.** At the end of month `T`, series `s` is visible only up to
   `T - lag_months(s)`. Implement this as one masking function and use it everywhere. Any
   feature or target value newer than the cutoff is leakage. Prove the mask works before modelling.
2. **Expanding-window backtesting only.** Never shuffle, never a random train/test split, never
   fit a scaler or hyperparameter on data that includes the test period.
3. **Hyperparameters chosen nested.** The outer rolling origin must never see its own target when
   a configuration is selected. If you pick a configuration by looking at out-of-sample scores,
   say so and label the result as optimistically biased.
4. **Baselines first.** Random walk, seasonal naive, and AR(AIC) are the bar. A model is only
   "better" if it beats them on the identical origin set, with a Diebold-Mariano test reported.
5. **No deep learning.** Gradient boosting at most. Depth of validation beats depth of network.
6. **Report losses.** If your model loses to the baseline, that is the finding. Do not tune until
   it wins and then present only the winner.
7. **Say what you cannot verify.** Sample size, revision risk, and calibration uncertainty are
   part of the result, not a footnote.

## Required deliverables

```
scripts/          data acquisition (if you re-pull), masking, EDA, backtest, tuning, intervals, regimes
data/             the panel you actually used, plus the lag table
reports/          eda.md, model_comparison.md, intervals.md, regime.md - each with tables and the caveats
app/              Streamlit app: forecast + interval with width + regime + scenario + download
README.md         what it does, how to run it, what the results are, what is unresolved
requirements.txt  pinned, with the Python version stated
```

## Acceptance criteria (a reviewer will check these)

- [ ] A script proves no column exposes data published after the forecast origin, and it exits
      non-zero if it does.
- [ ] Rolling-origin results include the baselines in the same table as your models.
- [ ] Every headline claim has a Diebold-Mariano test or an interval around it.
- [ ] Interval coverage is measured empirically against the nominal level, not assumed.
- [ ] The app prints interval width next to every forecast.
- [ ] A limitations section states: sample size, revision risk, what the sample cannot verify.

## Reference results (sanity anchors, not targets to beat)

See `REFERENCE_RESULTS.md`. A legitimate rebuild should land **within roughly ±10% MASE** of those
numbers on the same origins. If your model is dramatically better, assume you have leaked and go
looking for the leak before you celebrate - that is what happened the first time this was built.

## Environment

Python **3.11** (not 3.14 - see `PITFALLS.md`), pandas, numpy, scipy, statsmodels, lightgbm,
streamlit, tabulate. Pin them.

## Style

Reports in English, tables in markdown, numbers with units. No marketing adjectives. If something
is weak, say "weak" and quantify it.
