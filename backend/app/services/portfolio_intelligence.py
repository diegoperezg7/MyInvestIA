"""Structured portfolio intelligence and candidate impact analysis."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.services.fundamentals_service import get_fundamentals
from app.services.market_data import market_data_service
from app.services.quant_metrics import (
    TRADING_DAYS,
    align_return_series,
    annualized_return,
    annualized_volatility,
    beta,
    conditional_value_at_risk,
    contribution_to_risk,
    correlation_matrix,
    covariance_matrix,
    equal_weight_weights,
    inverse_volatility_weights,
    max_drawdown_from_returns,
    mean_variance_weights,
    normalize_weights,
    portfolio_returns,
    portfolio_volatility,
    returns_from_prices,
    risk_parity_weights,
    rolling_returns,
    rolling_volatility,
    sharpe_ratio,
    sortino_ratio,
    summarize_series,
    value_at_risk,
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _close_series(history: list[dict]) -> list[float]:
    return [
        float(point["close"])
        for point in history or []
        if point.get("close") not in (None, 0)
    ]


def _infer_sector(symbol: str, asset_type: str, fundamentals: dict | None) -> str:
    if fundamentals:
        company_info = fundamentals.get("company_info", {})
        if company_info.get("sector"):
            return str(company_info["sector"])
    if asset_type == "crypto":
        return "Crypto"
    etf_map = {
        "QQQ": "Technology",
        "SPY": "Broad Market",
        "XLK": "Technology",
        "XLF": "Financial Services",
        "XLV": "Healthcare",
        "XLE": "Energy",
        "XLI": "Industrials",
        "XLP": "Consumer Defensive",
        "XLU": "Utilities",
    }
    return etf_map.get(symbol.upper(), "Unknown")


def _infer_country(asset_type: str, fundamentals: dict | None) -> str:
    if fundamentals:
        company_info = fundamentals.get("company_info", {})
        if company_info.get("country"):
            return str(company_info["country"])
    if asset_type == "crypto":
        return "Global"
    return "Unknown"


def _infer_currency(quote: dict | None) -> str:
    return str((quote or {}).get("currency") or "USD")


def _build_exposures(
    holdings: list[dict],
    total_value: float,
    field: str,
) -> list[dict]:
    buckets: dict[str, float] = {}
    for holding in holdings:
        key = str(holding.get(field) or "Unknown")
        buckets[key] = buckets.get(key, 0.0) + float(holding.get("current_value", 0.0) or 0.0)
    items = [
        {
            "key": key,
            "weight": round(value / total_value, 6),
            "value": round(value, 2),
        }
        for key, value in buckets.items()
        if total_value > 0
    ]
    items.sort(key=lambda item: item["weight"], reverse=True)
    return items


def _build_concentration_summary(
    items: list[dict],
    *,
    label: str,
    warning_threshold: float,
) -> dict:
    weights = [float(item.get("weight", 0.0) or 0.0) for item in items]
    hhi = sum(weight**2 for weight in weights)
    alerts = [
        f"{label} concentration elevated in {item['key']} ({item['weight'] * 100:.1f}%)"
        for item in items
        if float(item.get("weight", 0.0) or 0.0) >= warning_threshold
    ]
    return {
        "items": items,
        "top_weight": round(max(weights) if weights else 0.0, 6),
        "hhi_score": round(hhi, 6),
        "alerts": alerts,
    }


def _build_correlation_payload(symbols: list[str], corr_matrix: np.ndarray) -> dict:
    if not symbols:
        return {
            "symbols": [],
            "matrix": [],
            "average_pairwise_correlation": 0.0,
            "high_correlations": [],
        }
    if len(symbols) == 1 or corr_matrix.size == 0:
        return {
            "symbols": symbols,
            "matrix": [[1.0]],
            "average_pairwise_correlation": 0.0,
            "high_correlations": [],
        }
    matrix = [
        [round(float(corr_matrix[row, col]), 6) for col in range(len(symbols))]
        for row in range(len(symbols))
    ]
    pair_values: list[float] = []
    high_correlations: list[dict] = []
    for row in range(len(symbols)):
        for col in range(row + 1, len(symbols)):
            value = float(corr_matrix[row, col])
            pair_values.append(value)
            if abs(value) >= 0.8:
                high_correlations.append(
                    {
                        "pair": f"{symbols[row]}/{symbols[col]}",
                        "value": round(value, 6),
                    }
                )
    return {
        "symbols": symbols,
        "matrix": matrix,
        "average_pairwise_correlation": round(
            float(np.mean(pair_values)) if pair_values else 0.0,
            6,
        ),
        "high_correlations": high_correlations,
    }


def _build_contribution_payload(
    symbols: list[str],
    weights: np.ndarray,
    ctr: np.ndarray,
) -> list[dict]:
    items = []
    for symbol, weight, contribution in zip(symbols, weights, ctr):
        items.append(
            {
                "symbol": symbol,
                "portfolio_weight": round(float(weight), 6),
                "risk_contribution": round(float(contribution), 6),
                "risk_share": round(float(contribution), 6),
            }
        )
    items.sort(key=lambda item: item["risk_share"], reverse=True)
    return items


def _strategy_payload(
    name: str,
    description: str,
    weights_map: dict[str, float],
    expected_returns: np.ndarray,
    cov_matrix: np.ndarray,
    symbols: list[str],
    risk_free_rate: float,
) -> dict:
    if not weights_map:
        return {
            "name": name,
            "description": description,
            "target_weights": [],
            "expected_return": 0.0,
            "expected_volatility": 0.0,
            "expected_sharpe": 0.0,
        }
    weights = np.array([weights_map[symbol] for symbol in symbols], dtype=np.float64)
    exp_return = float(expected_returns @ weights) if expected_returns.size else 0.0
    exp_vol = portfolio_volatility(weights, cov_matrix)
    exp_sharpe = (exp_return - risk_free_rate) / exp_vol if exp_vol > 1e-12 else 0.0
    return {
        "name": name,
        "description": description,
        "target_weights": [
            {"symbol": symbol, "weight": round(float(weights_map[symbol]), 6)}
            for symbol in symbols
        ],
        "expected_return": round(exp_return, 6),
        "expected_volatility": round(exp_vol, 6),
        "expected_sharpe": round(exp_sharpe, 6),
    }


def _build_rebalance_suggestions(
    holdings: list[dict],
    asset_concentration: dict,
    sector_concentration: dict,
    currency_concentration: dict,
    correlation_payload: dict,
    risk_metrics: dict,
) -> list[dict]:
    suggestions: list[dict] = []
    for item in asset_concentration.get("items", []):
        if item["weight"] >= 0.25:
            suggestions.append(
                {
                    "type": "rebalance",
                    "priority": "high",
                    "title": f"Reduce single-name concentration in {item['key']}",
                    "summary": f"{item['key']} represents {item['weight'] * 100:.1f}% of the portfolio.",
                    "action": "Review trimming or offsetting the position with diversifying exposures.",
                }
            )
    for item in sector_concentration.get("items", []):
        if item["weight"] >= 0.40:
            suggestions.append(
                {
                    "type": "sector",
                    "priority": "medium",
                    "title": f"Sector exposure concentrated in {item['key']}",
                    "summary": f"{item['key']} is {item['weight'] * 100:.1f}% of current exposure.",
                    "action": "Consider adding assets from underrepresented sectors or reducing overlap.",
                }
            )
    for item in currency_concentration.get("items", []):
        if item["weight"] >= 0.75:
            suggestions.append(
                {
                    "type": "currency",
                    "priority": "medium",
                    "title": f"Currency exposure concentrated in {item['key']}",
                    "summary": f"{item['key']} accounts for {item['weight'] * 100:.1f}% of portfolio value.",
                    "action": "If base-currency risk matters, diversify currency exposure or hedge explicitly.",
                }
            )
    for pair in correlation_payload.get("high_correlations", [])[:3]:
        suggestions.append(
            {
                "type": "correlation",
                "priority": "medium",
                "title": f"High correlation detected in {pair['pair']}",
                "summary": f"Pair correlation is {pair['value']:.2f}, reducing diversification benefit.",
                "action": "Treat the pair as a combined risk bucket when sizing positions.",
            }
        )
    if risk_metrics.get("annualized_volatility", 0.0) >= 0.30:
        suggestions.append(
            {
                "type": "risk",
                "priority": "medium",
                "title": "Portfolio volatility is elevated",
                "summary": f"Estimated annualized volatility is {risk_metrics['annualized_volatility'] * 100:.1f}%.",
                "action": "Compare current sizing with an inverse-volatility or risk-parity allocation.",
            }
        )
    if risk_metrics.get("max_drawdown", 0.0) <= -0.20:
        suggestions.append(
            {
                "type": "drawdown",
                "priority": "high",
                "title": "Historical drawdown profile is heavy",
                "summary": f"Observed max drawdown is {abs(risk_metrics['max_drawdown']) * 100:.1f}%.",
                "action": "Reassess position sizing, liquidity needs, and downside budget before adding risk.",
            }
        )
    return suggestions[:8]


def _candidate_impact_payload(
    holdings: list[dict],
    histories: dict[str, list[dict]],
    metadata: dict[str, dict],
    benchmark_history: list[dict],
    *,
    candidate_symbol: str,
    candidate_weight: float,
    candidate_history: list[dict] | None,
    candidate_metadata: dict | None,
    risk_free_rate: float,
) -> dict | None:
    if not candidate_history:
        return None

    base_returns_map = {
        symbol: returns_from_prices(_close_series(history))
        for symbol, history in histories.items()
    }
    base_symbols, base_matrix = align_return_series(base_returns_map)
    if len(base_symbols) < 1 or base_matrix.size == 0:
        return None

    holdings_by_symbol = {holding["symbol"]: holding for holding in holdings}
    ordered_base_holdings = [
        holdings_by_symbol[symbol]
        for symbol in base_symbols
        if symbol in holdings_by_symbol
    ]
    base_weights = normalize_weights([holding["current_value"] for holding in ordered_base_holdings])
    base_portfolio_returns = portfolio_returns(base_matrix, base_weights)

    candidate_returns = returns_from_prices(_close_series(candidate_history))
    if candidate_returns.size < 2:
        return None

    combined_map = dict(base_returns_map)
    combined_map[candidate_symbol] = candidate_returns
    symbols, combined_matrix = align_return_series(combined_map)
    if candidate_symbol not in symbols or combined_matrix.size == 0:
        return None

    adjusted_holdings = [
        holdings_by_symbol[symbol]
        for symbol in symbols
        if symbol in holdings_by_symbol and symbol != candidate_symbol
    ]
    current_weights = normalize_weights([holding["current_value"] for holding in adjusted_holdings])
    scaled_existing = current_weights * (1.0 - candidate_weight)
    combined_weights = np.append(scaled_existing, candidate_weight)

    ordered_symbols = [holding["symbol"] for holding in adjusted_holdings] + [candidate_symbol]
    reorder_index = [symbols.index(symbol) for symbol in ordered_symbols]
    ordered_matrix = combined_matrix[:, reorder_index]
    updated_returns = portfolio_returns(ordered_matrix, combined_weights)

    candidate_corr = 0.0
    aligned_candidate = ordered_matrix[:, -1]
    size = min(aligned_candidate.size, base_portfolio_returns.size)
    if size >= 2:
        candidate_corr = float(np.corrcoef(aligned_candidate[-size:], base_portfolio_returns[-size:])[0, 1])

    before_vol = annualized_volatility(base_portfolio_returns)
    after_vol = annualized_volatility(updated_returns)
    before_sharpe = sharpe_ratio(base_portfolio_returns, risk_free_rate=risk_free_rate)
    after_sharpe = sharpe_ratio(updated_returns, risk_free_rate=risk_free_rate)
    before_mdd = max_drawdown_from_returns(base_portfolio_returns)
    after_mdd = max_drawdown_from_returns(updated_returns)

    sector_before = _build_exposures(holdings, sum(item["current_value"] for item in holdings), "sector")
    diluted_existing = [
        {**holding, "current_value": holding["current_value"] * (1.0 - candidate_weight)}
        for holding in adjusted_holdings
    ]
    notional_total = sum(item["current_value"] for item in holdings)
    candidate_value = notional_total * candidate_weight
    sector = str((candidate_metadata or {}).get("sector") or "Unknown")
    enriched_candidate = {
        "symbol": candidate_symbol,
        "current_value": candidate_value,
        "sector": sector,
    }
    sector_after = _build_exposures(
        diluted_existing + [enriched_candidate],
        notional_total,
        "sector",
    )

    notes: list[str] = []
    if candidate_corr <= 0.3:
        notes.append("Candidate shows low correlation with the current portfolio.")
    elif candidate_corr >= 0.75:
        notes.append("Candidate is highly correlated with the current portfolio.")
    if after_vol < before_vol:
        notes.append("Adding the asset reduces estimated portfolio volatility.")
    elif after_vol > before_vol:
        notes.append("Adding the asset increases estimated portfolio volatility.")

    return {
        "symbol": candidate_symbol,
        "candidate_weight": round(candidate_weight, 6),
        "candidate_sector": sector,
        "correlation_to_portfolio": round(candidate_corr, 6),
        "volatility_delta": round(after_vol - before_vol, 6),
        "sharpe_delta": round(after_sharpe - before_sharpe, 6),
        "max_drawdown_delta": round(after_mdd - before_mdd, 6),
        "sector_exposure_before": sector_before,
        "sector_exposure_after": sector_after,
        "notes": notes,
    }


def analyze_portfolio_from_data(
    holdings: list[dict],
    histories: dict[str, list[dict]],
    metadata: dict[str, dict] | None = None,
    *,
    benchmark_history: list[dict] | None = None,
    candidate_symbol: str | None = None,
    candidate_weight: float = 0.10,
    candidate_history: list[dict] | None = None,
    candidate_metadata: dict | None = None,
    risk_free_rate: float = 0.02,
) -> dict:
    metadata = metadata or {}
    active_holdings = [
        {**holding, **metadata.get(holding["symbol"], {})}
        for holding in holdings
        if float(holding.get("current_value", 0.0) or 0.0) > 0
    ]
    if not active_holdings:
        return {
            "generated_at": _iso_now(),
            "total_value": 0.0,
            "holdings_count": 0,
            "allocation": [],
            "concentration": {"asset": {}, "sector": {}, "currency": {}},
            "risk_metrics": {},
            "correlation": {"symbols": [], "matrix": [], "average_pairwise_correlation": 0.0, "high_correlations": []},
            "rolling_metrics": {},
            "contribution_to_risk": [],
            "strategy_snapshots": [],
            "rebalance_suggestions": [],
            "candidate_impact": None,
            "warnings": ["No active holdings available for analysis."],
            "disclaimer": "Informational analytics only. This system does not execute trades or provide financial advice.",
        }

    total_value = sum(float(holding["current_value"]) for holding in active_holdings)
    for holding in active_holdings:
        holding["weight"] = float(holding["current_value"]) / total_value if total_value > 0 else 0.0

    returns_map = {
        symbol: returns_from_prices(_close_series(history))
        for symbol, history in histories.items()
    }
    symbols, returns_matrix = align_return_series(returns_map)
    warnings: list[str] = []
    if len(symbols) != len(active_holdings):
        missing = sorted({holding["symbol"] for holding in active_holdings} - set(symbols))
        if missing:
            warnings.append(f"Insufficient return history for: {', '.join(missing)}")

    holdings_by_symbol = {holding["symbol"]: holding for holding in active_holdings}
    ordered_holdings = [
        holdings_by_symbol[symbol]
        for symbol in symbols
        if symbol in holdings_by_symbol
    ]
    if not ordered_holdings or returns_matrix.size == 0:
        return {
            "generated_at": _iso_now(),
            "total_value": round(total_value, 2),
            "holdings_count": len(active_holdings),
            "allocation": [],
            "concentration": {"asset": {}, "sector": {}, "currency": {}},
            "risk_metrics": {},
            "correlation": {"symbols": [], "matrix": [], "average_pairwise_correlation": 0.0, "high_correlations": []},
            "rolling_metrics": {},
            "contribution_to_risk": [],
            "strategy_snapshots": [],
            "rebalance_suggestions": [],
            "candidate_impact": None,
            "warnings": warnings or ["Portfolio holdings do not have enough aligned history."],
            "disclaimer": "Informational analytics only. This system does not execute trades or provide financial advice.",
        }

    weights = normalize_weights([holding["current_value"] for holding in ordered_holdings])
    portfolio_ret = portfolio_returns(returns_matrix, weights)
    benchmark_returns = returns_from_prices(_close_series(benchmark_history or []))
    cov_matrix = covariance_matrix(returns_matrix)
    corr_matrix = correlation_matrix(returns_matrix)

    asset_allocation = [
        {
            "symbol": holding["symbol"],
            "name": holding.get("name", holding["symbol"]),
            "type": holding.get("type", "stock"),
            "weight": round(float(weight), 6),
            "current_value": round(float(holding["current_value"]), 2),
            "sector": holding.get("sector", "Unknown"),
            "currency": holding.get("currency", "USD"),
        }
        for holding, weight in zip(ordered_holdings, weights)
    ]
    asset_allocation.sort(key=lambda item: item["weight"], reverse=True)

    sector_items = _build_exposures(ordered_holdings, total_value, "sector")
    currency_items = _build_exposures(ordered_holdings, total_value, "currency")
    asset_items = [
        {
            "key": item["symbol"],
            "weight": item["weight"],
            "value": item["current_value"],
        }
        for item in asset_allocation
    ]

    annual_return = annualized_return(portfolio_ret)
    annual_vol = annualized_volatility(portfolio_ret)
    risk_metrics = {
        "annualized_return": round(annual_return, 6),
        "annualized_volatility": round(annual_vol, 6),
        "sharpe_ratio": round(sharpe_ratio(portfolio_ret, risk_free_rate=risk_free_rate), 6),
        "sortino_ratio": round(sortino_ratio(portfolio_ret, risk_free_rate=risk_free_rate), 6),
        "max_drawdown": round(max_drawdown_from_returns(portfolio_ret), 6),
        "beta": round(beta(portfolio_ret, benchmark_returns), 6),
        "var_95": round(value_at_risk(portfolio_ret, 0.95), 6),
        "cvar_95": round(conditional_value_at_risk(portfolio_ret, 0.95), 6),
        "daily_return_mean": round(float(np.mean(portfolio_ret)) if portfolio_ret.size else 0.0, 6),
    }

    rolling_metrics = {
        "returns_21d": summarize_series(rolling_returns(portfolio_ret, 21)),
        "returns_63d": summarize_series(rolling_returns(portfolio_ret, 63)),
        "volatility_21d": summarize_series(rolling_volatility(portfolio_ret, 21)),
        "volatility_63d": summarize_series(rolling_volatility(portfolio_ret, 63)),
    }

    ctr = contribution_to_risk(weights, cov_matrix)
    correlation_payload = _build_correlation_payload(symbols, corr_matrix)
    asset_concentration = _build_concentration_summary(
        asset_items,
        label="Asset",
        warning_threshold=0.25,
    )
    sector_concentration = _build_concentration_summary(
        sector_items,
        label="Sector",
        warning_threshold=0.40,
    )
    currency_concentration = _build_concentration_summary(
        currency_items,
        label="Currency",
        warning_threshold=0.75,
    )

    expected_returns = np.mean(returns_matrix, axis=0) * TRADING_DAYS
    strategy_snapshots = [
        _strategy_payload(
            "equal_weight",
            "Same capital weight assigned to each current holding.",
            equal_weight_weights(symbols),
            expected_returns,
            cov_matrix,
            symbols,
            risk_free_rate,
        ),
        _strategy_payload(
            "inverse_volatility",
            "Weights scaled inversely to each asset's observed volatility.",
            inverse_volatility_weights(symbols, returns_matrix),
            expected_returns,
            cov_matrix,
            symbols,
            risk_free_rate,
        ),
        _strategy_payload(
            "mean_variance",
            "Long-only mean-variance heuristic based on sample returns and covariance.",
            mean_variance_weights(symbols, expected_returns, cov_matrix),
            expected_returns,
            cov_matrix,
            symbols,
            risk_free_rate,
        ),
        _strategy_payload(
            "risk_parity",
            "Approximate equal-risk-contribution allocation using the sample covariance matrix.",
            risk_parity_weights(symbols, cov_matrix),
            expected_returns,
            cov_matrix,
            symbols,
            risk_free_rate,
        ),
    ]

    candidate_weight = max(0.01, min(candidate_weight, 0.30))
    candidate_impact = None
    if candidate_symbol:
        candidate_impact = _candidate_impact_payload(
            ordered_holdings,
            histories,
            metadata,
            benchmark_history or [],
            candidate_symbol=candidate_symbol.upper(),
            candidate_weight=candidate_weight,
            candidate_history=candidate_history,
            candidate_metadata=candidate_metadata,
            risk_free_rate=risk_free_rate,
        )
        if candidate_impact is None:
            warnings.append(f"Candidate impact unavailable for {candidate_symbol.upper()}.")

    return {
        "generated_at": _iso_now(),
        "total_value": round(total_value, 2),
        "holdings_count": len(ordered_holdings),
        "allocation": asset_allocation,
        "concentration": {
            "asset": asset_concentration,
            "sector": sector_concentration,
            "currency": currency_concentration,
        },
        "risk_metrics": risk_metrics,
        "correlation": correlation_payload,
        "rolling_metrics": rolling_metrics,
        "contribution_to_risk": _build_contribution_payload(symbols, weights, ctr),
        "strategy_snapshots": strategy_snapshots,
        "rebalance_suggestions": _build_rebalance_suggestions(
            ordered_holdings,
            asset_concentration,
            sector_concentration,
            currency_concentration,
            correlation_payload,
            risk_metrics,
        ),
        "candidate_impact": candidate_impact,
        "warnings": warnings,
        "disclaimer": "Informational analytics only. This system does not execute trades or provide financial advice.",
    }


async def build_portfolio_intelligence(
    holdings: list[dict],
    *,
    candidate_symbol: str | None = None,
    candidate_asset_type: str | None = None,
    candidate_weight: float = 0.10,
    risk_free_rate: float = 0.02,
) -> dict:
    positions = [
        holding
        for holding in holdings
        if float(holding.get("current_value", 0.0) or 0.0) > 0
    ]
    if not positions:
        return analyze_portfolio_from_data([], {}, {})

    histories: dict[str, list[dict]] = {}
    metadata: dict[str, dict] = {}

    async def _load_position(holding: dict) -> None:
        symbol = holding["symbol"].upper()
        history_task = market_data_service.get_history(symbol, period="1y", interval="1d")
        fundamentals_task = get_fundamentals(symbol)
        quote_task = market_data_service.get_quote(symbol, holding.get("type"))
        history, fundamentals, quote = await asyncio.gather(
            history_task,
            fundamentals_task,
            quote_task,
            return_exceptions=True,
        )
        histories[symbol] = history if isinstance(history, list) else []
        fundamentals_data = fundamentals if isinstance(fundamentals, dict) else None
        quote_data = quote if isinstance(quote, dict) else None
        metadata[symbol] = {
            "sector": _infer_sector(symbol, str(holding.get("type", "stock")), fundamentals_data),
            "country": _infer_country(str(holding.get("type", "stock")), fundamentals_data),
            "currency": _infer_currency(quote_data),
        }

    await asyncio.gather(*[_load_position(holding) for holding in positions])
    benchmark_history = await market_data_service.get_history("SPY", period="1y", interval="1d")

    candidate_history: list[dict] | None = None
    candidate_metadata: dict | None = None
    if candidate_symbol:
        candidate_upper = candidate_symbol.upper()
        fundamentals_task = get_fundamentals(candidate_upper)
        quote_task = market_data_service.get_quote(candidate_upper, candidate_asset_type)
        candidate_history_task = market_data_service.get_history(candidate_upper, period="1y", interval="1d")
        fundamentals, quote, history = await asyncio.gather(
            fundamentals_task,
            quote_task,
            candidate_history_task,
            return_exceptions=True,
        )
        fundamentals_data = fundamentals if isinstance(fundamentals, dict) else None
        quote_data = quote if isinstance(quote, dict) else None
        candidate_history = history if isinstance(history, list) else []
        candidate_type = candidate_asset_type or "stock"
        candidate_metadata = {
            "sector": _infer_sector(candidate_upper, candidate_type, fundamentals_data),
            "country": _infer_country(candidate_type, fundamentals_data),
            "currency": _infer_currency(quote_data),
        }

    return analyze_portfolio_from_data(
        positions,
        histories,
        metadata,
        benchmark_history=benchmark_history,
        candidate_symbol=candidate_symbol,
        candidate_weight=candidate_weight,
        candidate_history=candidate_history,
        candidate_metadata=candidate_metadata,
        risk_free_rate=risk_free_rate,
    )
