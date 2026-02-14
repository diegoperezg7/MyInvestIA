"""Portfolio risk analytics service."""

import logging
import math
from typing import Any

import numpy as np
import yfinance as yf

from app.services import cache

logger = logging.getLogger(__name__)

RISK_TTL = 900  # 15 min cache


async def calculate_portfolio_risk(holdings: list[dict]) -> dict:
    """Calculate comprehensive risk metrics for a portfolio.

    holdings: list of {"symbol": str, "quantity": float, "current_value": float}
    """
    if not holdings:
        return _empty_response()

    symbols = [h["symbol"] for h in holdings]
    values = [h.get("current_value", 0) for h in holdings]
    portfolio_value = sum(values)
    if portfolio_value <= 0:
        return _empty_response()

    weights = np.array([v / portfolio_value for v in values])

    # Check cache
    cache_key = f"portfolio_risk:{':'.join(sorted(symbols))}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Fetch 1Y daily returns
    try:
        tickers_str = " ".join(symbols)
        if len(symbols) == 1:
            data = yf.download(tickers_str, period="1y", interval="1d", progress=False)
            if data.empty:
                return _empty_response()
            closes = data["Close"].dropna()
            returns_df = closes.pct_change().dropna()
            returns_matrix = returns_df.values.reshape(-1, 1)
        else:
            data = yf.download(tickers_str, period="1y", interval="1d", progress=False, group_by="ticker")
            if data.empty:
                return _empty_response()

            # Build returns matrix
            returns_list = []
            valid_symbols = []
            valid_weights = []
            for i, sym in enumerate(symbols):
                try:
                    closes = data[sym]["Close"].dropna() if sym in data.columns.get_level_values(0) else data["Close"].dropna()
                    if len(closes) < 30:
                        continue
                    rets = closes.pct_change().dropna()
                    returns_list.append(rets.values)
                    valid_symbols.append(sym)
                    valid_weights.append(weights[i])
                except Exception:
                    continue

            if not returns_list:
                return _empty_response()

            # Align lengths
            min_len = min(len(r) for r in returns_list)
            returns_matrix = np.column_stack([r[-min_len:] for r in returns_list])
            weights = np.array(valid_weights)
            weights = weights / weights.sum()
            symbols = valid_symbols

        # Portfolio daily returns
        portfolio_returns = returns_matrix @ weights if returns_matrix.ndim == 2 else returns_matrix.flatten()

        metrics = _calculate_metrics(portfolio_returns, portfolio_value, symbols, returns_matrix)
        concentration = _calculate_concentration(symbols, values, portfolio_value)
        correlation = _calculate_correlation(symbols, returns_matrix)
        stress_tests = _run_stress_tests(portfolio_value, metrics.get("beta", 1.0))

        result = {
            "metrics": metrics,
            "concentration": concentration,
            "correlation": correlation,
            "stress_tests": stress_tests,
            "portfolio_value": round(portfolio_value, 2),
        }

        cache.set(cache_key, result, RISK_TTL)
        return result

    except Exception as e:
        logger.error("Portfolio risk calculation failed: %s", e)
        return _empty_response()


def _calculate_metrics(
    portfolio_returns: np.ndarray,
    portfolio_value: float,
    symbols: list[str],
    returns_matrix: np.ndarray,
) -> dict:
    """Calculate VaR, Sharpe, Sortino, Beta, Max Drawdown, Volatility."""
    daily_mean = float(np.mean(portfolio_returns))
    daily_std = float(np.std(portfolio_returns))

    # VaR (Historical)
    var_95 = float(np.percentile(portfolio_returns, 5)) * portfolio_value
    var_99 = float(np.percentile(portfolio_returns, 1)) * portfolio_value

    # Annual metrics
    annual_return = daily_mean * 252
    annual_vol = daily_std * math.sqrt(252)
    risk_free_rate = 0.045  # ~4.5% US T-bill rate

    # Sharpe ratio
    sharpe = (annual_return - risk_free_rate) / annual_vol if annual_vol > 0 else 0.0

    # Sortino ratio
    downside_returns = portfolio_returns[portfolio_returns < 0]
    downside_std = float(np.std(downside_returns)) * math.sqrt(252) if len(downside_returns) > 0 else annual_vol
    sortino = (annual_return - risk_free_rate) / downside_std if downside_std > 0 else 0.0

    # Beta vs SPY
    beta = 1.0
    try:
        spy_data = yf.download("SPY", period="1y", interval="1d", progress=False)
        if not spy_data.empty:
            spy_returns = spy_data["Close"].pct_change().dropna().values
            min_len = min(len(portfolio_returns), len(spy_returns))
            pr = portfolio_returns[-min_len:]
            sr = spy_returns[-min_len:]
            cov = np.cov(pr, sr)
            beta = float(cov[0, 1] / cov[1, 1]) if cov[1, 1] > 0 else 1.0
    except Exception:
        pass

    # Max drawdown
    cumulative = np.cumprod(1 + portfolio_returns)
    peak = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - peak) / peak
    max_drawdown = float(np.min(drawdowns))

    return {
        "var_95": round(abs(var_95), 2),
        "var_99": round(abs(var_99), 2),
        "sharpe_ratio": round(sharpe, 3),
        "sortino_ratio": round(sortino, 3),
        "beta": round(beta, 3),
        "max_drawdown": round(abs(max_drawdown), 4),
        "annual_volatility": round(annual_vol, 4),
        "daily_return_mean": round(daily_mean, 6),
    }


def _calculate_concentration(symbols: list[str], values: list[float], total: float) -> dict:
    """Calculate portfolio concentration metrics."""
    positions = sorted(
        [{"symbol": s, "weight": round(v / total, 4), "value": round(v, 2)} for s, v in zip(symbols, values)],
        key=lambda x: x["weight"],
        reverse=True,
    )

    weights = [p["weight"] for p in positions]
    top3 = sum(weights[:3])

    # HHI (Herfindahl-Hirschman Index): sum of squared weights
    hhi = sum(w ** 2 for w in weights)
    # Diversification score: 1 - HHI (0 = concentrated, 1 = diversified)
    diversification = round(1 - hhi, 4)

    alerts = []
    for p in positions:
        if p["weight"] > 0.25:
            alerts.append(f"{p['symbol']} is {p['weight']*100:.1f}% of portfolio (>25%)")

    return {
        "positions": positions,
        "top3_concentration": round(top3, 4),
        "hhi_score": round(hhi, 4),
        "diversification_score": diversification,
        "alerts": alerts,
    }


def _calculate_correlation(symbols: list[str], returns_matrix: np.ndarray) -> dict:
    """Calculate correlation matrix between holdings."""
    if returns_matrix.ndim == 1 or returns_matrix.shape[1] < 2:
        return {"symbols": symbols, "matrix": [[1.0]], "high_correlations": []}

    corr = np.corrcoef(returns_matrix.T)
    matrix = [[round(float(corr[i, j]), 4) for j in range(len(symbols))] for i in range(len(symbols))]

    high_corr = []
    for i in range(len(symbols)):
        for j in range(i + 1, len(symbols)):
            val = float(corr[i, j])
            if abs(val) > 0.8:
                high_corr.append({
                    "pair": f"{symbols[i]}/{symbols[j]}",
                    "value": round(val, 4),
                })

    return {
        "symbols": symbols,
        "matrix": matrix,
        "high_correlations": high_corr,
    }


def _run_stress_tests(portfolio_value: float, beta: float) -> list[dict]:
    """Run historical stress test scenarios."""
    scenarios = [
        {"name": "2008 Financial Crisis", "description": "Global financial meltdown", "market_drop": -0.55},
        {"name": "2020 COVID Crash", "description": "Pandemic market selloff", "market_drop": -0.34},
        {"name": "2022 Rate Shock", "description": "Fed aggressive rate hikes", "market_drop": -0.25},
        {"name": "10% Correction", "description": "Standard market correction", "market_drop": -0.10},
        {"name": "20% Bear Market", "description": "Bear market territory", "market_drop": -0.20},
    ]

    results = []
    for s in scenarios:
        est_loss = portfolio_value * s["market_drop"] * beta
        est_loss_pct = s["market_drop"] * beta
        results.append({
            "name": s["name"],
            "description": s["description"],
            "market_drop": s["market_drop"],
            "estimated_portfolio_loss": round(abs(est_loss), 2),
            "estimated_portfolio_loss_pct": round(abs(est_loss_pct), 4),
        })

    return results


def _empty_response() -> dict:
    return {
        "metrics": {
            "var_95": 0, "var_99": 0, "sharpe_ratio": 0, "sortino_ratio": 0,
            "beta": 0, "max_drawdown": 0, "annual_volatility": 0, "daily_return_mean": 0,
        },
        "concentration": {
            "positions": [], "top3_concentration": 0, "hhi_score": 0,
            "diversification_score": 0, "alerts": [],
        },
        "correlation": {"symbols": [], "matrix": [], "high_correlations": []},
        "stress_tests": [],
        "portfolio_value": 0,
    }
