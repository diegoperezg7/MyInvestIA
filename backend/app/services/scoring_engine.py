"""Explainable asset scoring engine built on structured data and calculations."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.services.enhanced_sentiment_service import get_enhanced_sentiment
from app.services.fundamentals_service import get_fundamentals
from app.services.macro_intelligence import get_all_macro_indicators, get_macro_summary
from app.services.market_data import market_data_service
from app.services.portfolio_intelligence import build_portfolio_intelligence
from app.services.quant_scoring import compute_quant_scores
from app.services.store import store
from app.services.technical_analysis import compute_all_indicators


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _score_from_signed_factor(value: float) -> float:
    return _clip(50.0 + value * 50.0)


def _weights() -> dict[str, float]:
    weights = {
        "fundamentals_score": float(getattr(settings, "score_weight_fundamentals", 0.25)),
        "technical_score": float(getattr(settings, "score_weight_technical", 0.25)),
        "sentiment_score": float(getattr(settings, "score_weight_sentiment", 0.15)),
        "macro_score": float(getattr(settings, "score_weight_macro", 0.15)),
        "portfolio_fit_score": float(getattr(settings, "score_weight_portfolio_fit", 0.20)),
    }
    total = sum(max(weight, 0.0) for weight in weights.values())
    if total <= 1e-12:
        return {
            key: round(1.0 / len(weights), 6)
            for key in weights
        }
    return {
        key: round(max(weight, 0.0) / total, 6)
        for key, weight in weights.items()
    }


def _component(
    name: str,
    value: float,
    explanation: str,
    *,
    inputs_used: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    sources: list[str] | None = None,
    weight_applied: float = 0.0,
) -> dict:
    return {
        "name": name,
        "value": round(_clip(value), 4),
        "explanation": explanation,
        "inputs_used": inputs_used or {},
        "warnings": warnings or [],
        "timestamp": _iso_now(),
        "sources": sources or [],
        "weight_applied": round(weight_applied, 6),
    }


def _score_fundamentals(fundamentals: dict | None, *, weight: float) -> dict:
    warnings: list[str] = []
    if not fundamentals:
        warnings.append("Fundamentals data unavailable; using neutral baseline.")
        return _component(
            "fundamentals_score",
            50.0,
            "No structured fundamentals were available, so the score remains neutral.",
            warnings=warnings,
            weight_applied=weight,
        )

    ratios = fundamentals.get("ratios", {})
    growth = fundamentals.get("growth", {})
    company_info = fundamentals.get("company_info", {})

    roe = float(ratios.get("roe", 0.0) or 0.0)
    profit_margins = float(ratios.get("profit_margins", 0.0) or 0.0)
    debt_to_equity = float(ratios.get("debt_to_equity", 0.0) or 0.0)
    current_ratio = float(ratios.get("current_ratio", 0.0) or 0.0)
    forward_pe = float(ratios.get("pe_forward") or ratios.get("pe_trailing") or 0.0)
    price_to_book = float(ratios.get("price_to_book", 0.0) or 0.0)
    revenue_growth = float(growth.get("revenue_growth", 0.0) or 0.0)
    earnings_growth = float(growth.get("earnings_growth", 0.0) or 0.0)

    profitability = _clip(50 + roe * 120 + profit_margins * 90)
    balance_sheet = _clip(55 - min(debt_to_equity / 250.0, 1.0) * 30 + min(current_ratio, 3.0) * 5)
    valuation = _clip(75 - min(forward_pe / 35.0, 1.5) * 20 - min(price_to_book / 8.0, 1.5) * 10)
    growth_score = _clip(50 + revenue_growth * 35 + earnings_growth * 45)
    value = round((profitability + balance_sheet + valuation + growth_score) / 4.0, 4)

    if not company_info.get("sector"):
        warnings.append("Sector classification missing; peer and context checks are limited.")
    if forward_pe <= 0:
        warnings.append("Valuation ratios are incomplete or non-positive.")

    explanation = (
        f"Fundamentals score reflects profitability ({profitability:.1f}), balance-sheet quality ({balance_sheet:.1f}), "
        f"valuation ({valuation:.1f}), and growth ({growth_score:.1f})."
    )
    return _component(
        "fundamentals_score",
        value,
        explanation,
        inputs_used={
            "roe": roe,
            "profit_margins": profit_margins,
            "debt_to_equity": debt_to_equity,
            "current_ratio": current_ratio,
            "pe_forward_or_trailing": forward_pe,
            "price_to_book": price_to_book,
            "revenue_growth": revenue_growth,
            "earnings_growth": earnings_growth,
        },
        warnings=warnings,
        sources=[str(fundamentals.get("source") or fundamentals.get("source_provider") or "fundamentals")],
        weight_applied=weight,
    )


def _score_technical(
    history: list[dict],
    macro_indicators: list[dict],
    enhanced_sentiment: dict | None,
    *,
    weight: float,
) -> tuple[dict, dict]:
    warnings: list[str] = []
    if not history or len(history) < 30:
        warnings.append("At least 30 history points are required for a technical score.")
        component = _component(
            "technical_score",
            50.0,
            "Technical score remains neutral because there is not enough price history.",
            warnings=warnings,
            weight_applied=weight,
        )
        return component, {}

    closes = [float(point["close"]) for point in history]
    technical_data = compute_all_indicators(closes)
    quant_scores = compute_quant_scores(history, macro_indicators, enhanced_sentiment)
    factors = quant_scores.get("factors", {})
    technical_factor = sum(
        float(factors.get(name, 0.0) or 0.0)
        for name in (
            "trend",
            "momentum",
            "volume",
            "mean_reversion",
            "support_resistance",
            "candlestick",
        )
    ) / 6.0
    value = _score_from_signed_factor(technical_factor)

    rsi_value = technical_data.get("rsi", {}).get("value")
    macd_signal = technical_data.get("macd", {}).get("signal")
    overall_signal = technical_data.get("overall_signal", "neutral")
    explanation = (
        f"Technical score is driven by the quant factor bundle ({technical_factor:+.2f}), "
        f"RSI at {rsi_value if rsi_value is not None else 'N/A'}, MACD signal '{macd_signal}', "
        f"and an overall technical regime of '{overall_signal}'."
    )

    return (
        _component(
            "technical_score",
            value,
            explanation,
            inputs_used={
                "rsi": rsi_value,
                "macd_signal": macd_signal,
                "overall_signal": overall_signal,
                "quant_factors": {
                    key: factors.get(key, 0.0)
                    for key in (
                        "trend",
                        "momentum",
                        "volume",
                        "mean_reversion",
                        "support_resistance",
                        "candlestick",
                    )
                },
                "quant_verdict": quant_scores.get("verdict"),
                "quant_confidence": quant_scores.get("confidence"),
            },
            warnings=warnings,
            sources=["technical_analysis", "quant_scoring"],
            weight_applied=weight,
        ),
        quant_scores,
    )


def _score_sentiment(enhanced_sentiment: dict | None, *, weight: float) -> dict:
    warnings: list[str] = []
    if not enhanced_sentiment:
        warnings.append("Enhanced sentiment unavailable; sentiment score is neutral.")
        return _component(
            "sentiment_score",
            50.0,
            "No structured sentiment payload was available.",
            warnings=warnings,
            weight_applied=weight,
        )

    unified_score = float(enhanced_sentiment.get("unified_score", 0.0) or 0.0)
    coverage = float(enhanced_sentiment.get("coverage_confidence", 0.0) or 0.0)
    source_count = len(enhanced_sentiment.get("sources", []) or [])
    value = _clip(50 + unified_score * 35 + coverage * 15)
    if coverage < 0.2:
        warnings.append("Sentiment coverage is thin; treat the reading as low-confidence.")
    explanation = (
        f"Sentiment score reflects a unified sentiment of {unified_score:+.2f} with "
        f"coverage confidence {coverage:.2f} across {source_count} sources."
    )
    return _component(
        "sentiment_score",
        value,
        explanation,
        inputs_used={
            "unified_score": unified_score,
            "coverage_confidence": coverage,
            "sources_count": source_count,
            "label": enhanced_sentiment.get("unified_label", "neutral"),
        },
        warnings=warnings,
        sources=[source.get("source_name", "sentiment") for source in enhanced_sentiment.get("sources", [])],
        weight_applied=weight,
    )


def _score_macro(
    macro_indicators: list[dict],
    macro_summary: dict,
    *,
    weight: float,
) -> dict:
    warnings: list[str] = []
    if not macro_indicators:
        warnings.append("Macro indicators unavailable; using neutral macro score.")
        return _component(
            "macro_score",
            50.0,
            "No macro indicators were available for structured scoring.",
            warnings=warnings,
            weight_applied=weight,
        )

    vix = next((float(item.get("value", 0.0) or 0.0) for item in macro_indicators if "VIX" in item.get("name", "")), 0.0)
    dxy_change = next((float(item.get("change_percent", 0.0) or 0.0) for item in macro_indicators if "Dollar" in item.get("name", "")), 0.0)
    ten_year = next((float(item.get("value", 0.0) or 0.0) for item in macro_indicators if "10-Year" in item.get("name", "")), 0.0)
    bill_13w = next((float(item.get("value", 0.0) or 0.0) for item in macro_indicators if "13-Week" in item.get("name", "")), 0.0)
    curve_spread = ten_year - bill_13w if ten_year and bill_13w else 0.0

    environment = macro_summary.get("environment", "neutral")
    value = 55.0
    if environment == "risk-off":
        value -= 12.0
    elif environment == "risk-on":
        value += 8.0
    value -= min(max(vix - 20.0, 0.0), 20.0) * 0.8
    value -= max(dxy_change, 0.0) * 1.2
    value += min(max(curve_spread, -2.0), 2.0) * 4.0
    value = _clip(value)

    explanation = (
        f"Macro score uses the current macro regime '{environment}', VIX at {vix:.2f}, "
        f"DXY daily change {dxy_change:+.2f}%, and yield-curve spread {curve_spread:+.2f}."
    )
    return _component(
        "macro_score",
        value,
        explanation,
        inputs_used={
            "environment": environment,
            "risk_level": macro_summary.get("risk_level", "unknown"),
            "vix": vix,
            "dxy_change_percent": dxy_change,
            "yield_curve_spread": curve_spread,
        },
        warnings=warnings,
        sources=sorted(
            {
                str(item.get("source") or item.get("source_provider") or "macro")
                for item in macro_indicators
            }
        ),
        weight_applied=weight,
    )


def _score_portfolio_fit(
    symbol: str,
    portfolio_intelligence: dict | None,
    *,
    weight: float,
) -> dict:
    warnings: list[str] = []
    if not portfolio_intelligence:
        warnings.append("Portfolio context unavailable; using neutral portfolio-fit score.")
        return _component(
            "portfolio_fit_score",
            50.0,
            "No current portfolio context was available to evaluate fit.",
            warnings=warnings,
            weight_applied=weight,
        )

    candidate_impact = portfolio_intelligence.get("candidate_impact")
    if not candidate_impact:
        warnings.append("Candidate impact could not be estimated; portfolio-fit score is neutral.")
        return _component(
            "portfolio_fit_score",
            50.0,
            "Candidate fit was not computed because simulated portfolio impact is unavailable.",
            warnings=warnings,
            weight_applied=weight,
        )

    value = 50.0
    correlation = float(candidate_impact.get("correlation_to_portfolio", 0.0) or 0.0)
    volatility_delta = float(candidate_impact.get("volatility_delta", 0.0) or 0.0)
    sharpe_delta = float(candidate_impact.get("sharpe_delta", 0.0) or 0.0)
    if correlation <= 0.3:
        value += 12.0
    elif correlation >= 0.75:
        value -= 15.0
    value += max(min(sharpe_delta * 20.0, 15.0), -15.0)
    value -= max(min(volatility_delta * 120.0, 15.0), -15.0)

    current_allocation = portfolio_intelligence.get("allocation", [])
    for item in current_allocation:
        if item.get("symbol") == symbol and float(item.get("weight", 0.0) or 0.0) >= 0.20:
            value -= 12.0
            warnings.append("Asset is already a meaningful portfolio weight; adding more may increase concentration.")
            break

    explanation = (
        f"Portfolio-fit score uses simulated add-to-portfolio impact, with correlation {correlation:+.2f}, "
        f"volatility delta {volatility_delta:+.3f}, and Sharpe delta {sharpe_delta:+.3f}."
    )
    return _component(
        "portfolio_fit_score",
        _clip(value),
        explanation,
        inputs_used={
            "candidate_impact": candidate_impact,
            "current_holdings_count": portfolio_intelligence.get("holdings_count", 0),
        },
        warnings=warnings,
        sources=["portfolio_intelligence"],
        weight_applied=weight,
    )


def _total_component(components: dict[str, dict], weights: dict[str, float]) -> dict:
    total_value = 0.0
    for key, component in components.items():
        total_value += float(component["value"]) * weights[key]
    total_warnings = []
    for component in components.values():
        total_warnings.extend(component.get("warnings", []))

    if total_value >= 75:
        rating = "strong_positive"
    elif total_value >= 60:
        rating = "positive"
    elif total_value >= 40:
        rating = "neutral"
    elif total_value >= 25:
        rating = "cautious"
    else:
        rating = "negative"

    return _component(
        "total_score",
        total_value,
        f"Total score is the weighted blend of fundamentals, technicals, sentiment, macro, and portfolio fit. Current rating: {rating}.",
        inputs_used={
            "weights": weights,
            "components": {
                key: components[key]["value"]
                for key in components
            },
            "rating": rating,
        },
        warnings=total_warnings,
        sources=sorted(
            {
                source
                for component in components.values()
                for source in component.get("sources", [])
            }
        ),
        weight_applied=1.0,
    )


async def _portfolio_positions(user_id: str, tenant_id: str | None) -> list[dict]:
    raw_holdings = store.get_holdings(user_id, tenant_id)
    if not raw_holdings:
        return []

    async def _enrich(holding: dict) -> dict:
        quote = await market_data_service.get_quote(holding["symbol"], holding.get("type"))
        price = float((quote or {}).get("price") or holding.get("avg_buy_price", 0.0) or 0.0)
        return {
            "symbol": holding["symbol"].upper(),
            "name": holding.get("name", holding["symbol"].upper()),
            "type": holding.get("type", "stock"),
            "quantity": float(holding.get("quantity", 0.0) or 0.0),
            "avg_buy_price": float(holding.get("avg_buy_price", 0.0) or 0.0),
            "current_value": round(price * float(holding.get("quantity", 0.0) or 0.0), 4),
        }

    return [
        item
        for item in await asyncio.gather(*[_enrich(holding) for holding in raw_holdings])
        if item["current_value"] > 0
    ]


async def build_asset_score(
    symbol: str,
    *,
    asset_type: str | None = None,
    user_id: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    symbol_upper = symbol.upper()
    weights = _weights()

    quote_task = market_data_service.get_quote(symbol_upper, asset_type)
    history_task = market_data_service.get_history(symbol_upper, period="1y", interval="1d")
    fundamentals_task = get_fundamentals(symbol_upper)
    sentiment_task = get_enhanced_sentiment(symbol_upper)
    macro_task = get_all_macro_indicators()

    quote, history, fundamentals, enhanced_sentiment, macro_indicators = await asyncio.gather(
        quote_task,
        history_task,
        fundamentals_task,
        sentiment_task,
        macro_task,
        return_exceptions=True,
    )

    quote_data = quote if isinstance(quote, dict) else None
    history_data = history if isinstance(history, list) else []
    fundamentals_data = fundamentals if isinstance(fundamentals, dict) else None
    sentiment_data = enhanced_sentiment if isinstance(enhanced_sentiment, dict) else None
    macro_data = macro_indicators if isinstance(macro_indicators, list) else []
    macro_summary = get_macro_summary(macro_data)

    portfolio_intelligence = None
    if user_id:
        positions = await _portfolio_positions(user_id, tenant_id)
        if positions:
            portfolio_intelligence = await build_portfolio_intelligence(
                positions,
                candidate_symbol=symbol_upper,
                candidate_asset_type=asset_type,
                candidate_weight=float(getattr(settings, "portfolio_candidate_weight", 0.10)),
            )

    fundamentals_component = _score_fundamentals(
        fundamentals_data,
        weight=weights["fundamentals_score"],
    )
    technical_component, quant_scores = _score_technical(
        history_data,
        macro_data,
        sentiment_data,
        weight=weights["technical_score"],
    )
    sentiment_component = _score_sentiment(
        sentiment_data,
        weight=weights["sentiment_score"],
    )
    macro_component = _score_macro(
        macro_data,
        macro_summary,
        weight=weights["macro_score"],
    )
    portfolio_fit_component = _score_portfolio_fit(
        symbol_upper,
        portfolio_intelligence,
        weight=weights["portfolio_fit_score"],
    )

    components = {
        "fundamentals_score": fundamentals_component,
        "technical_score": technical_component,
        "sentiment_score": sentiment_component,
        "macro_score": macro_component,
        "portfolio_fit_score": portfolio_fit_component,
    }
    total_score = _total_component(components, weights)

    return {
        "symbol": symbol_upper,
        "asset_type": asset_type or "stock",
        "quote": {
            "price": float((quote_data or {}).get("price", 0.0) or 0.0),
            "change_percent": float((quote_data or {}).get("change_percent", 0.0) or 0.0),
            "name": (quote_data or {}).get("name", symbol_upper),
            "currency": (quote_data or {}).get("currency", "USD"),
        },
        "fundamentals_score": fundamentals_component,
        "technical_score": technical_component,
        "sentiment_score": sentiment_component,
        "macro_score": macro_component,
        "portfolio_fit_score": portfolio_fit_component,
        "total_score": total_score,
        "weights": weights,
        "quant_overlay": quant_scores,
        "portfolio_context": {
            "available": bool(portfolio_intelligence),
            "candidate_impact": (portfolio_intelligence or {}).get("candidate_impact"),
        },
        "generated_at": _iso_now(),
        "decision_support_only": True,
        "disclaimer": "Informational scoring only. This output is not financial advice and does not trigger trade execution.",
    }
