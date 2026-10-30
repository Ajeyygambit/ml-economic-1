# ACCEPTANCE CHECKLIST - what a reviewer will actually test

Tick each one with evidence (a command, a file path, a table). "It works" is not evidence.

## A. Setup and reproducibility

- [ ] `requirements.txt` exists, pinned, and states the Python version (3.11).
- [ ] A clean environment built from it runs the pipeline end to end without manual steps.
- [ ] `README.md` states what the project does, how to run it, and what the current results are -
      a reader can get from clone to running app without asking a question.

## B. Data integrity

- [ ] `data/manifest.json` (or equivalent) records the source URL and fetch timestamp of every series.
- [ ] Every unit in the dictionary is correct. Specifically: trade values are ringgit in the source
      and RM million in the panel - check 2015-01 exports = 62,971,395,081 ringgit.
- [ ] Missing values are left missing, not forward-filled across gaps, and the imputation policy is
      stated if one exists.
- [ ] Two independent series agreeing is cited where it exists (exports agreed across
      `trade_headline` and `trade_sitc_1d` to 0.000%).

## C. Leakage

- [ ] One mask function, one lag table, no duplicated lag logic.
- [ ] A checker script that exits non-zero when any column exposes data after the origin.
- [ ] The checker is run **before** any model, and its output is in the report.
- [ ] The report states the consequence explicitly: at origin `T`, the newest usable IPI is `T-2`.

## D. Validation

- [ ] Expanding window, rolling origin, no shuffling.
- [ ] Baselines (random walk, mean-of-3, AR(AIC)) appear in the **same** table as the ML models.
- [ ] Hyperparameter selection is nested; if it is not, the result is labelled biased.
- [ ] Diebold-Mariano (or an equivalent) reported for every headline comparison.
- [ ] Number of origins reported per horizon.
- [ ] When VAR-style models are used, a stability guard exists and the count of rejected origins
      is reported; comparisons are made on matched origins.

## E. Uncertainty

- [ ] Empirical coverage measured against the nominal level, at 80% and 95%.
- [ ] The failure direction is stated (under-coverage is worse than over-coverage, and why).
- [ ] Mean interval width is reported in the same units as the target, not just as a ratio.
- [ ] The report says what the sample size **cannot** verify (for ~60 origins, coverage is only
      resolvable to about ±5 pp).

## F. Interpretation

- [ ] R² of the champion model is reported, not just its error.
- [ ] Any coefficient presented in a scenario is checked for how many distinct values its regressor
      takes. `opr` has six in this sample - that is a regime dummy, not an elasticity.
- [ ] Disagreement between specifications is surfaced, not hidden.

## G. Application

- [ ] Every forecast is shown with its interval **and the interval width**.
- [ ] The competing baseline is visible next to the champion.
- [ ] P(target < 0) or an equivalent decision-relevant transformation is shown.
- [ ] The current regime label appears with the measured error penalty, if a regime model is used.
- [ ] Warnings fire when inputs fall outside the training range.
- [ ] A downloadable brief carries the same caveats as the page.

## H. Honesty

- [ ] At least one place in the reports says the model **lost**.
- [ ] Limitations section: sample size, revision risk (no public real-time vintage database for
      Malaysia), calibration uncertainty, structural break in exports.
- [ ] No number is reported that is not reproducible from the committed scripts and data.

## Automatic gate

```bash
python handoff/verify_submission.py <path-to-submission>
```

Checks the file layout, the panel contract, the lag table completeness, and the plausibility of
reported MASE values. It cannot check the modelling - that is what sections D to H are for.
