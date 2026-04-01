"""Reusable quantitative metrics for asset and portfolio analytics."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

TRADING_DAYS = 252


def _as_array(values: list[float] | np.ndarray) -> np.ndarray:
    return np.asarray(values, dtype=np.float64)


def returns_from_prices(prices: list[float] | np.ndarray) -> np.ndarray:
    arr = _as_array(prices)
    if arr.size < 2:
        return np.array([], dtype=np.float64)
    valid = arr[np.isfinite(arr)]
    if valid.size < 2:
        return np.array([], dtype=np.float64)
    return np.diff(valid) / np.maximum(valid[:-1], 1e-12)


def annualized_return(
    returns: list[float] | np.ndarray,
    periods_per_year: int = TRADING_DAYS,
) -> float:
    arr = _as_array(returns)
    if arr.size == 0:
        return 0.0
    compounded = float(np.prod(1.0 + arr))
    years = arr.size / periods_per_year
    if years <= 0 or compounded <= 0:
        return 0.0
    return compounded ** (1 / years) - 1


def annualized_volatility(
    returns: list[float] | np.ndarray,
    periods_per_year: int = TRADING_DAYS,
) -> float:
    arr = _as_array(returns)
    if arr.size < 2:
        return 0.0
    return float(np.std(arr, ddof=1) * math.sqrt(periods_per_year))


def sharpe_ratio(
    returns: list[float] | np.ndarray,
    risk_free_rate: float = 0.02,
    periods_per_year: int = TRADING_DAYS,
) -> float:
    arr = _as_array(returns)
    if arr.size < 2:
        return 0.0
    rf_per_period = risk_free_rate / periods_per_year
    excess = arr - rf_per_period
    std = float(np.std(excess, ddof=1))
    if std <= 1e-12:
        return 0.0
    return float(np.mean(excess) / std * math.sqrt(periods_per_year))


def sortino_ratio(
    returns: list[float] | np.ndarray,
    risk_free_rate: float = 0.02,
    periods_per_year: int = TRADING_DAYS,
) -> float:
    arr = _as_array(returns)
    if arr.size < 2:
        return 0.0
    rf_per_period = risk_free_rate / periods_per_year
    excess = arr - rf_per_period
    downside = excess[excess < 0]
    downside_std = float(np.std(downside, ddof=1)) if downside.size >= 2 else 0.0
    if downside_std <= 1e-12:
        return 0.0
    return float(np.mean(excess) / downside_std * math.sqrt(periods_per_year))


def max_drawdown_from_prices(prices: list[float] | np.ndarray) -> float:
    arr = _as_array(prices)
    if arr.size < 2:
        return 0.0
    wealth = arr / max(arr[0], 1e-12)
    peaks = np.maximum.accumulate(wealth)
    drawdowns = wealth / np.maximum(peaks, 1e-12) - 1.0
    return float(np.min(drawdowns))


def max_drawdown_from_returns(returns: list[float] | np.ndarray) -> float:
    arr = _as_array(returns)
    if arr.size == 0:
        return 0.0
    wealth = np.cumprod(1.0 + arr)
    peaks = np.maximum.accumulate(wealth)
    drawdowns = wealth / np.maximum(peaks, 1e-12) - 1.0
    return float(np.min(drawdowns))


def value_at_risk(
    returns: list[float] | np.ndarray,
    confidence: float = 0.95,
) -> float:
    arr = _as_array(returns)
    if arr.size == 0:
        return 0.0
    percentile = max(0.0, min(100.0, (1.0 - confidence) * 100.0))
    return float(np.percentile(arr, percentile))


def conditional_value_at_risk(
    returns: list[float] | np.ndarray,
    confidence: float = 0.95,
) -> float:
    arr = _as_array(returns)
    if arr.size == 0:
        return 0.0
    threshold = value_at_risk(arr, confidence)
    tail = arr[arr <= threshold]
    if tail.size == 0:
        return threshold
    return float(np.mean(tail))


def beta(
    returns: list[float] | np.ndarray,
    benchmark_returns: list[float] | np.ndarray,
) -> float:
    asset = _as_array(returns)
    benchmark = _as_array(benchmark_returns)
    size = min(asset.size, benchmark.size)
    if size < 2:
        return 0.0
    asset = asset[-size:]
    benchmark = benchmark[-size:]
    cov = np.cov(asset, benchmark)
    benchmark_var = float(cov[1, 1])
    if benchmark_var <= 1e-12:
        return 0.0
    return float(cov[0, 1] / benchmark_var)


def rolling_returns(
    returns: list[float] | np.ndarray,
    window: int,
) -> list[float | None]:
    arr = _as_array(returns)
    if arr.size == 0 or window <= 0:
        return [None] * arr.size
    result: list[float | None] = [None] * arr.size
    if arr.size < window:
        return result
    for index in range(window - 1, arr.size):
        window_returns = arr[index - window + 1 : index + 1]
        result[index] = float(np.prod(1.0 + window_returns) - 1.0)
    return result


def rolling_volatility(
    returns: list[float] | np.ndarray,
    window: int,
    periods_per_year: int = TRADING_DAYS,
) -> list[float | None]:
    arr = _as_array(returns)
    if arr.size == 0 or window <= 1:
        return [None] * arr.size
    result: list[float | None] = [None] * arr.size
    if arr.size < window:
        return result
    for index in range(window - 1, arr.size):
        window_returns = arr[index - window + 1 : index + 1]
        result[index] = float(np.std(window_returns, ddof=1) * math.sqrt(periods_per_year))
    return result


def summarize_series(values: list[float | None]) -> dict[str, Any]:
    clean = [float(item) for item in values if item is not None and np.isfinite(item)]
    if not clean:
        return {
            "latest": 0.0,
            "average": 0.0,
            "minimum": 0.0,
            "maximum": 0.0,
            "samples": 0,
        }
    return {
        "latest": round(clean[-1], 6),
        "average": round(float(np.mean(clean)), 6),
        "minimum": round(float(np.min(clean)), 6),
        "maximum": round(float(np.max(clean)), 6),
        "samples": len(clean),
    }


def align_return_series(series_map: dict[str, list[float] | np.ndarray]) -> tuple[list[str], np.ndarray]:
    valid_items: list[tuple[str, np.ndarray]] = []
    for symbol, values in series_map.items():
        arr = _as_array(values)
        if arr.size >= 2:
            valid_items.append((symbol, arr))
    if not valid_items:
        return [], np.empty((0, 0), dtype=np.float64)
    min_len = min(arr.size for _, arr in valid_items)
    symbols = [symbol for symbol, _ in valid_items]
    matrix = np.column_stack([arr[-min_len:] for _, arr in valid_items])
    return symbols, matrix


def covariance_matrix(
    returns_matrix: np.ndarray,
    periods_per_year: int = TRADING_DAYS,
) -> np.ndarray:
    if returns_matrix.ndim != 2 or returns_matrix.size == 0:
        return np.empty((0, 0), dtype=np.float64)
    if returns_matrix.shape[1] == 1:
        variance = float(np.var(returns_matrix[:, 0], ddof=1)) if returns_matrix.shape[0] >= 2 else 0.0
        return np.array([[variance * periods_per_year]], dtype=np.float64)
    return np.cov(returns_matrix, rowvar=False) * periods_per_year


def correlation_matrix(returns_matrix: np.ndarray) -> np.ndarray:
    if returns_matrix.ndim != 2 or returns_matrix.shape[1] < 2:
        width = returns_matrix.shape[1] if returns_matrix.ndim == 2 else 0
        return np.eye(width, dtype=np.float64)
    return np.corrcoef(returns_matrix, rowvar=False)


def portfolio_returns(
    returns_matrix: np.ndarray,
    weights: list[float] | np.ndarray,
) -> np.ndarray:
    if returns_matrix.ndim != 2 or returns_matrix.size == 0:
        return np.array([], dtype=np.float64)
    weight_arr = normalize_weights(weights)
    if weight_arr.size != returns_matrix.shape[1]:
        raise ValueError("weights size must match return matrix width")
    return returns_matrix @ weight_arr


def portfolio_volatility(
    weights: list[float] | np.ndarray,
    cov_matrix: np.ndarray,
) -> float:
    weight_arr = normalize_weights(weights)
    if cov_matrix.size == 0 or cov_matrix.shape[0] != weight_arr.size:
        return 0.0
    variance = float(weight_arr.T @ cov_matrix @ weight_arr)
    return math.sqrt(max(variance, 0.0))


def normalize_weights(weights: list[float] | np.ndarray) -> np.ndarray:
    arr = _as_array(weights)
    if arr.size == 0:
        return arr
    arr = np.maximum(arr, 0.0)
    total = float(np.sum(arr))
    if total <= 1e-12:
        return np.repeat(1.0 / arr.size, arr.size)
    return arr / total


def marginal_contribution_to_risk(
    weights: list[float] | np.ndarray,
    cov_matrix: np.ndarray,
) -> np.ndarray:
    weight_arr = normalize_weights(weights)
    if cov_matrix.size == 0 or cov_matrix.shape[0] != weight_arr.size:
        return np.zeros(weight_arr.size, dtype=np.float64)
    port_vol = portfolio_volatility(weight_arr, cov_matrix)
    if port_vol <= 1e-12:
        return np.zeros(weight_arr.size, dtype=np.float64)
    return (cov_matrix @ weight_arr) / port_vol


def contribution_to_risk(
    weights: list[float] | np.ndarray,
    cov_matrix: np.ndarray,
) -> np.ndarray:
    weight_arr = normalize_weights(weights)
    mctr = marginal_contribution_to_risk(weight_arr, cov_matrix)
    port_vol = portfolio_volatility(weight_arr, cov_matrix)
    if port_vol <= 1e-12:
        return np.zeros(weight_arr.size, dtype=np.float64)
    return (weight_arr * mctr) / port_vol


def equal_weight_weights(symbols: list[str]) -> dict[str, float]:
    if not symbols:
        return {}
    weight = round(1.0 / len(symbols), 6)
    return {symbol: weight for symbol in symbols}


def inverse_volatility_weights(
    symbols: list[str],
    returns_matrix: np.ndarray,
) -> dict[str, float]:
    if not symbols or returns_matrix.ndim != 2:
        return {}
    vols = np.std(returns_matrix, axis=0, ddof=1)
    inverse = np.array([1.0 / max(vol, 1e-6) for vol in vols], dtype=np.float64)
    weights = normalize_weights(inverse)
    return {symbol: round(float(weight), 6) for symbol, weight in zip(symbols, weights)}


def mean_variance_weights(
    symbols: list[str],
    expected_returns: np.ndarray,
    cov_matrix: np.ndarray,
) -> dict[str, float]:
    if not symbols or expected_returns.size == 0 or cov_matrix.size == 0:
        return {}
    try:
        raw = np.linalg.pinv(cov_matrix) @ expected_returns
    except np.linalg.LinAlgError:
        raw = expected_returns
    weights = normalize_weights(np.maximum(raw, 0.0))
    if np.allclose(weights, 0.0):
        return equal_weight_weights(symbols)
    return {symbol: round(float(weight), 6) for symbol, weight in zip(symbols, weights)}


def risk_parity_weights(
    symbols: list[str],
    cov_matrix: np.ndarray,
    *,
    iterations: int = 200,
) -> dict[str, float]:
    if not symbols or cov_matrix.size == 0:
        return {}
    n_assets = len(symbols)
    weights = np.repeat(1.0 / n_assets, n_assets)
    target = 1.0 / n_assets
    for _ in range(iterations):
        contributions = contribution_to_risk(weights, cov_matrix)
        if contributions.size == 0:
            break
        safe = np.maximum(contributions, 1e-6)
        weights *= target / safe
        weights = normalize_weights(weights)
    return {symbol: round(float(weight), 6) for symbol, weight in zip(symbols, weights)}
