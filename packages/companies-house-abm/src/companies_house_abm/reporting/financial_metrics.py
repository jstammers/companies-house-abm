"""Validation metrics for the financial-crash module.

Implements the return stylised facts (Cont 2001) and the crash-specific
diagnostics listed in ``docs/financial-market-crash.md`` §7 (Tiers 1-2).
"""

from __future__ import annotations

import numpy as np


def autocorrelation(x: np.ndarray, max_lag: int) -> np.ndarray:
    """Sample autocorrelation of ``x`` at lags 1..max_lag."""
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    n = len(x)
    denom = np.dot(x, x)
    if denom <= 0 or n <= max_lag:
        return np.zeros(max_lag)
    return np.array(
        [np.dot(x[: n - lag], x[lag:]) / denom for lag in range(1, max_lag + 1)]
    )


def hill_tail_exponent(returns: np.ndarray, tail_fraction: float = 0.1) -> float:
    """Hill (1975) estimator of the tail index of ``|returns|``.

    A value near 3 matches the "inverse cubic law" widely reported for
    equity returns (Cont 2001); lower values indicate fatter tails.
    """
    abs_returns = np.sort(np.abs(np.asarray(returns, dtype=float)))
    abs_returns = abs_returns[abs_returns > 0]
    n = len(abs_returns)
    k = max(int(n * tail_fraction), 5)
    if n < k + 1:
        return float("nan")
    tail = abs_returns[-k:]
    threshold = abs_returns[-k - 1]
    if threshold <= 0:
        return float("nan")
    log_ratios = np.log(tail / threshold)
    total = np.sum(log_ratios)
    return float(k / total) if total > 0 else float("nan")


def skewness(x: np.ndarray) -> float:
    """Sample skewness."""
    x = np.asarray(x, dtype=float)
    std = x.std()
    if std <= 0:
        return 0.0
    return float(np.mean(((x - x.mean()) / std) ** 3))


def excess_kurtosis(x: np.ndarray) -> float:
    """Sample excess kurtosis (0 for a Gaussian)."""
    x = np.asarray(x, dtype=float)
    std = x.std()
    if std <= 0:
        return 0.0
    return float(np.mean(((x - x.mean()) / std) ** 4) - 3.0)


def leverage_effect(returns: np.ndarray) -> float:
    """corr(r_t, |r_{t+1}|); negative = past falls precede higher volatility."""
    returns = np.asarray(returns, dtype=float)
    if len(returns) < 3:
        return float("nan")
    r = returns[:-1]
    abs_future = np.abs(returns[1:])
    if r.std() <= 0 or abs_future.std() <= 0:
        return float("nan")
    return float(np.corrcoef(r, abs_future)[0, 1])


def max_drawdown(prices: np.ndarray) -> float:
    """Largest peak-to-trough fractional decline."""
    prices = np.asarray(prices, dtype=float)
    if len(prices) == 0:
        return 0.0
    running_max = np.maximum.accumulate(prices)
    drawdown = prices / running_max - 1.0
    return float(drawdown.min())


def procyclicality(leverage_series: np.ndarray, price_index: np.ndarray) -> float:
    """corr(aggregate leverage, price level).

    > 0 means leverage is procyclical — it rises with prices and collapses
    in a crash, the pattern validated against FINRA margin debt (§7, Tier 2).
    """
    leverage_series = np.asarray(leverage_series, dtype=float)
    price_index = np.asarray(price_index, dtype=float)
    mask = np.isfinite(leverage_series) & np.isfinite(price_index)
    if mask.sum() < 3:
        return float("nan")
    if leverage_series[mask].std() <= 0 or price_index[mask].std() <= 0:
        return float("nan")
    return float(np.corrcoef(leverage_series[mask], price_index[mask])[0, 1])


def volume_spike_ratio(
    volumes: np.ndarray, crash_window: slice, baseline_window: slice
) -> float:
    """Ratio of mean activity in ``crash_window`` to ``baseline_window``.

    Used against a proxy for traded volume (e.g. margin-call counts or
    absolute order flow) to test "volume spikes on the way down" (§7, Tier 2).
    """
    volumes = np.asarray(volumes, dtype=float)
    baseline = volumes[baseline_window].mean()
    if baseline <= 0:
        return float("nan")
    return float(volumes[crash_window].mean() / baseline)


def stylised_facts_report(returns: np.ndarray, max_lag: int = 20) -> dict:
    """Tier 1 stylised-facts diagnostics (Cont 2001) for a return series."""
    returns = np.asarray(returns, dtype=float)
    returns = returns[np.isfinite(returns)]
    acf_returns = autocorrelation(returns, max_lag)
    acf_abs = autocorrelation(np.abs(returns), max_lag)
    return {
        "n_obs": len(returns),
        "mean": float(np.mean(returns)) if len(returns) else float("nan"),
        "std": float(np.std(returns)) if len(returns) else float("nan"),
        "skewness": skewness(returns),
        "excess_kurtosis": excess_kurtosis(returns),
        "tail_exponent": hill_tail_exponent(returns),
        "acf_return_lag1": float(acf_returns[0]) if len(acf_returns) else float("nan"),
        "acf_return_mean_abs": (
            float(np.mean(np.abs(acf_returns))) if len(acf_returns) else float("nan")
        ),
        "acf_abs_return_lag1": float(acf_abs[0]) if len(acf_abs) else float("nan"),
        "acf_abs_return_decay": acf_abs.tolist(),
        "leverage_effect": leverage_effect(returns),
    }
