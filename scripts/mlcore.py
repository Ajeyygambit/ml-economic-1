#!/usr/bin/env python3
"""
ML Economic 1 (Ajey) - shared machinery for the modelling scripts.

One place that defines:
  * the target and horizons,
  * the masked feature matrix (publication lags from data/publication_lag.csv),
  * the rolling-origin split,
  * the AR(AIC) baseline,
  * the LightGBM configuration grid,
  * MASE and the Diebold-Mariano test.

Every model script imports from here so the mask, the origins and the scoring are
identical across experiments. Duplicating that logic is how leakage creeps back in.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.arima.model import ARIMA

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

TARGET = "ipi_growth_yoy"
HORIZONS = (1, 3, 6, 12)
MIN_TRAIN = 36

# name -> (column, publication lag, extra lag)
FEATURES = {
    "ipi_yoy_l1": (TARGET, 2, 1), "ipi_yoy_l2": (TARGET, 2, 2), "ipi_yoy_l3": (TARGET, 2, 3),
    "ipi_yoy_l6": (TARGET, 2, 6), "ipi_yoy_l12": (TARGET, 2, 12),
    "exp_yoy_l1": ("exports_growth_yoy", 1, 1), "exp_yoy_l2": ("exports_growth_yoy", 1, 2),
    "exp_yoy_l12": ("exports_growth_yoy", 1, 12),
    "cpi_yoy": ("cpi_inflation_yoy", 1, 0), "cpi_yoy_l2": ("cpi_inflation_yoy", 1, 2),
    "u_rate": ("u_rate", 2, 0), "ppi_yoy": ("ppi_growth_yoy", 2, 0),
    "li_diff": ("li_leading_diffusion", 3, 0), "opr": ("opr", 0, 0),
    "myr_usd_l1": ("myr_per_usd", 1, 1),
}

CONFIGS = {
    "default": dict(n_estimators=300, learning_rate=0.05, num_leaves=7, min_child_samples=8,
                    subsample=0.8, colsample_bytree=0.8),
    "regularised": dict(n_estimators=150, learning_rate=0.03, num_leaves=3,
                        min_child_samples=15, subsample=0.8, colsample_bytree=0.6),
    "heavy": dict(n_estimators=400, learning_rate=0.02, num_leaves=4, min_child_samples=20,
                  subsample=0.7, colsample_bytree=0.5, reg_lambda=5.0),
    "linear_leaves": dict(n_estimators=100, learning_rate=0.05, num_leaves=3,
                          min_child_samples=12, linear_tree=True),
}


def load_panel() -> tuple[pd.DataFrame, pd.Series]:
    panel = pd.read_csv(ROOT / "data" / "panel_monthly.csv", dtype={"month": str})
    panel["i"] = panel["month"].str[:4].astype(int) * 12 + panel["month"].str[5:7].astype(int)
    panel = panel.set_index("i")
    return panel, panel[TARGET]


def build_features(panel: pd.DataFrame) -> pd.DataFrame:
    cols = {}
    for name, (col, lag, extra) in FEATURES.items():
        cols[name] = panel[col].shift(lag + extra)
    return pd.DataFrame(cols)


def origins_for(y: pd.Series, panel: pd.DataFrame, h: int) -> list[int]:
    tgt = y.shift(-h)
    first = y.dropna().index.min()
    return [i for i in panel.index if i >= first and not pd.isna(tgt.get(i, np.nan))]


def training_set(F: pd.DataFrame, y: pd.Series, h: int, origins: list[int], upto: int):
    """All (features, realised target) pairs strictly before `upto`."""
    tgt = y.shift(-h)
    idx = np.array([i for i in origins if i < upto])
    if len(idx) == 0:
        return None, None
    X, t = F.loc[idx], tgt.loc[idx].values
    ok = ~np.isnan(t) & X.notna().all(axis=1).values
    return X[ok], t[ok]


def lgbm(params: dict, X, t, **over):
    m = lgb.LGBMRegressor(random_state=0, verbose=-1, subsample_freq=1, **{**params, **over})
    m.fit(X, t)
    return m


def ar_forecast(y: pd.Series, origin: int, h: int, lag_y: int = 2, return_conf: bool = False):
    """AR(p) with p by AIC, iterated from the newest visible month."""
    hist = y[y.index <= origin - lag_y].dropna()
    if len(hist) < 24:
        return (np.nan, np.nan, np.nan) if return_conf else np.nan
    best = None
    for p in range(0, 5):
        try:
            fit = ARIMA(hist.values, order=(p, 0, 0)).fit()
        except Exception:
            continue
        if best is None or fit.aic < best.aic:
            best = fit
    if best is None:
        return (np.nan, np.nan, np.nan) if return_conf else np.nan
    steps = h + lag_y
    try:
        fc = best.get_forecast(steps)
        pred = float(np.asarray(fc.predicted_mean)[-1])
        if not return_conf:
            return pred
        ci = np.asarray(fc.conf_int(alpha=0.2))[-1]     # 80%
        ci95 = np.asarray(fc.conf_int(alpha=0.05))[-1]  # 95%
        return pred, (float(ci[0]), float(ci[1])), (float(ci95[0]), float(ci95[1]))
    except Exception:
        return (np.nan, (np.nan, np.nan), (np.nan, np.nan)) if return_conf else np.nan


def mase(pred: np.ndarray, actual: np.ndarray, base: np.ndarray) -> float:
    d = np.nanmean(np.abs(base - actual))
    return float(np.nanmean(np.abs(pred - actual)) / d)


def dm_test(e1: np.ndarray, e2: np.ndarray, h: int) -> tuple[float, float]:
    """Diebold-Mariano on squared errors, Newey-West with lag h-1."""
    d = e1 ** 2 - e2 ** 2
    n = len(d)
    mu, lrv = d.mean(), np.var(d, ddof=0)
    for lag in range(1, h):
        lrv += 2 * (1 - lag / h) * np.cov(d[lag:], d[:-lag])[0, 1]
    stat = mu / np.sqrt(lrv / n)
    return float(stat), float(2 * (1 - stats.norm.cdf(abs(stat))))


def pinball(actual, lower, upper, alpha: float) -> float:
    """Mean pinball (quantile) loss for the two interval bounds; lower alpha = sharper."""
    q_lo, q_hi = alpha / 2, 1 - alpha / 2
    lo = np.where(actual >= lower, q_lo * (actual - lower), (q_lo - 1) * (actual - lower))
    hi = np.where(actual >= upper, q_hi * (actual - upper), (q_hi - 1) * (actual - upper))
    return float(np.mean(lo + hi))
