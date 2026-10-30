# START HERE - handing this project to another model

This folder contains everything needed for a different LLM to rebuild the Malaysian macro
forecasting system from scratch. It is self-contained: prompt, spec, data contract, reference
results, known traps, and a checklist to judge the result.

## What is in here

| file | what it is | who reads it |
|---|---|---|
| `PROMPT.md` | the instruction to paste. Self-contained. | the model |
| `SPEC.md` | the technical contract: target, lags, feature set, model ladder, what was found | the model |
| `PITFALLS.md` | 13 traps that cost time in the first build, with symptoms and fixes | the model |
| `REFERENCE_RESULTS.md` | the first build's numbers as sanity anchors, plus "if yours is better, assume leakage" | the model, and you when grading |
| `ACCEPTANCE_CHECKLIST.md` | what a reviewer tests, section by section | you |
| `verify_submission.py` | runnable gate: file layout, panel contract, lag coverage, MASE plausibility | you |
| `data/` | the panel, the lag table, the OPR series, GDP - the exact vintage | the model |

## Three ways to run it

### 1. Chat model (Claude, ChatGPT, Gemini) - smallest useful version

Attach `data/panel_monthly.csv` and `data/publication_lag.csv`, then paste:

> Read PROMPT.md and SPEC.md (below). Build the system described. The two attached CSVs are the
> data. Report the rolling-origin table with baselines included, the coverage audit, and the
> limitations. Do not report any number you did not compute.

then paste the contents of `PROMPT.md` and `SPEC.md`. Add `PITFALLS.md` if the model has room -
it will save it from the exact mistakes listed there.

Chat models cannot run a long backtest reliably in one turn. Expect it to produce code you then
run yourself, not finished results.

### 2. Coding agent (Claude Code, Codex CLI, Cursor, Copilot agent) - the real option

Best path. Put the whole folder somewhere and tell the agent:

```
Read handoff/PROMPT.md, handoff/SPEC.md and handoff/PITFALLS.md.
Rebuild the system in this repository. The data in handoff/data/ is the fixed vintage - use it.
Run every script you write and paste the real output. Do not report a number you did not compute.
When you are done, run handoff/verify_submission.py and fix what it flags.
```

The agent can create the environment, run the backtests and iterate. This is the version that can
actually finish the job.

### 3. Fresh repository (clean-room rebuild, for a second opinion)

```bash
mkdir ~/ml-economic-rebuild && cd ~/ml-economic-rebuild
git init
cp -r /path/to/handoff/* .
# hand the folder to the agent as above
```

A clean-room rebuild is the useful comparison: if two independent implementations land within
±10% MASE of the reference numbers, the result is a property of the data, not of one person's
pipeline.

## How to grade what comes back

1. Run `python handoff/verify_submission.py <submission>` - objective checks only.
2. Open `ACCEPTANCE_CHECKLIST.md` and tick D to H by hand. Those are the ones that matter:
   baselines in the same table, nested selection, DM tests, measured coverage, reported R²,
   a limitations section, and at least one place where the model **lost**.
3. Compare against `REFERENCE_RESULTS.md`. A dramatically better result is a leakage signal, not
   a win.

## What "done" looks like

- Baselines and ML models in one table, same origins, with a Diebold-Mariano test.
- Intervals whose coverage was measured, not assumed, and whose width is printed next to the
  forecast.
- A regime label justified by measured error differences, with the cell sizes shown.
- A Streamlit app carrying every caveat the report carries.
- A limitations section that names the sample size, the revision risk, and what the sample
  cannot verify.
