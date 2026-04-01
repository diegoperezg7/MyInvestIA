"""Structured alert scoring service built on technical, sentiment, filings, and portfolio context."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.schemas.alerting import StructuredAlert
from app.schemas.asset import AlertSeverity, AlertType, SuggestedAction
from app.services.enhanced_sentiment_service import get_enhanced_sentiment
from app.services.macro_intelligence import get_all_macro_indicators, get_macro_summary
from app.services.market_data import market_data_service
from app.services.portfolio_intelligence import build_portfolio_intelligence
from app.services.sec_service import get_company_filings
from app.services.technical_analysis import compute_all_indicators

logger = logging.getLogger(__name__)

RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
RSI_EXTREME_OVERSOLD = 20
RSI_EXTREME_OVERBOUGHT = 80
PRICE_SPIKE_THRESHOLD = 5.0
PRICE_DROP_THRESHOLD = -5.0

SEVERITY_ORDER = {
    AlertSeverity.CRITICAL: 0,
    AlertSeverity.HIGH: 1,
    AlertSeverity.MEDIUM: 2,
    AlertSeverity.LOW: 3,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clip(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _source_names(sentiment: dict | None) -> list[str]:
    if not sentiment:
        return []
    return [
        str(source.get("source_name") or source.get("provider") or "sentiment")
        for source in sentiment.get("sources", [])
    ]


def _make_alert(
    alert_type: AlertType,
    severity: AlertSeverity,
    title: str,
    description: str,
    reasoning: str,
    confidence: float,
    action: SuggestedAction,
    *,
    symbol: str | None = None,
    reason: str = "",
    evidence: list[dict] | None = None,
    sources: list[str] | None = None,
    warnings: list[str] | None = None,
) -> StructuredAlert:
    return StructuredAlert(
        id=str(uuid.uuid4()),
        type=alert_type,
        severity=severity,
        title=title,
        description=description,
        reasoning=reasoning,
        reason=reason or reasoning,
        evidence=evidence or [],
        confidence=round(_clip(confidence), 2),
        suggested_action=action,
        created_at=_now_iso(),
        asset_symbol=symbol,
        sources=sources or [],
        warnings=warnings or [],
    )


def _price_move_alert(symbol: str, quote: dict) -> list[StructuredAlert]:
    alerts: list[StructuredAlert] = []
    change_pct = float(quote.get("change_percent", 0.0) or 0.0)
    if change_pct >= PRICE_SPIKE_THRESHOLD:
        severity = AlertSeverity.HIGH if change_pct >= 8.0 else AlertSeverity.MEDIUM
        alerts.append(
            _make_alert(
                AlertType.PRICE,
                severity,
                f"{symbol} surging +{change_pct:.1f}%",
                f"{symbol} is up {change_pct:.1f}% today with unusually strong upside pressure.",
                f"Single-day move of +{change_pct:.1f}% exceeds the alert threshold and deserves catalyst review.",
                min(0.5 + abs(change_pct) / 20.0, 0.9),
                SuggestedAction.MONITOR,
                symbol=symbol,
                evidence=[
                    {
                        "category": "price",
                        "summary": "Daily percentage move",
                        "value": round(change_pct, 2),
                        "source": "market_data",
                        "timestamp": _now_iso(),
                    }
                ],
                sources=["market_data"],
            )
        )
    elif change_pct <= PRICE_DROP_THRESHOLD:
        severity = AlertSeverity.HIGH if change_pct <= -8.0 else AlertSeverity.MEDIUM
        alerts.append(
            _make_alert(
                AlertType.PRICE,
                severity,
                f"{symbol} dropping {change_pct:.1f}%",
                f"{symbol} is down {change_pct:.1f}% today with heavy selling pressure.",
                f"Single-day move of {change_pct:.1f}% exceeds the downside alert threshold and may reflect a material catalyst.",
                min(0.5 + abs(change_pct) / 20.0, 0.9),
                SuggestedAction.MONITOR,
                symbol=symbol,
                evidence=[
                    {
                        "category": "price",
                        "summary": "Daily percentage move",
                        "value": round(change_pct, 2),
                        "source": "market_data",
                        "timestamp": _now_iso(),
                    }
                ],
                sources=["market_data"],
            )
        )
    return alerts


def _technical_alerts(symbol: str, indicators: dict) -> list[StructuredAlert]:
    alerts: list[StructuredAlert] = []
    rsi_data = indicators.get("rsi", {})
    rsi_val = rsi_data.get("value")

    if rsi_val is not None:
        if rsi_val <= RSI_EXTREME_OVERSOLD:
            alerts.append(
                _make_alert(
                    AlertType.TECHNICAL,
                    AlertSeverity.HIGH,
                    f"{symbol} extremely oversold (RSI {rsi_val:.0f})",
                    f"{symbol} RSI at {rsi_val:.1f} indicates extreme oversold conditions.",
                    f"RSI below {RSI_EXTREME_OVERSOLD} often reflects forced selling or exhaustion. This improves reversal odds but does not guarantee one.",
                    0.65,
                    SuggestedAction.BUY,
                    symbol=symbol,
                    evidence=[
                        {
                            "category": "technical",
                            "summary": "RSI value",
                            "value": round(float(rsi_val), 2),
                            "source": "technical_analysis",
                            "timestamp": _now_iso(),
                        }
                    ],
                    sources=["technical_analysis"],
                )
            )
        elif rsi_val <= RSI_OVERSOLD:
            alerts.append(
                _make_alert(
                    AlertType.TECHNICAL,
                    AlertSeverity.MEDIUM,
                    f"{symbol} oversold (RSI {rsi_val:.0f})",
                    f"{symbol} RSI at {rsi_val:.1f} has moved into oversold territory.",
                    f"RSI below {RSI_OVERSOLD} suggests downside extension relative to recent price action.",
                    0.55,
                    SuggestedAction.MONITOR,
                    symbol=symbol,
                    evidence=[
                        {
                            "category": "technical",
                            "summary": "RSI value",
                            "value": round(float(rsi_val), 2),
                            "source": "technical_analysis",
                            "timestamp": _now_iso(),
                        }
                    ],
                    sources=["technical_analysis"],
                )
            )
        elif rsi_val >= RSI_EXTREME_OVERBOUGHT:
            alerts.append(
                _make_alert(
                    AlertType.TECHNICAL,
                    AlertSeverity.HIGH,
                    f"{symbol} extremely overbought (RSI {rsi_val:.0f})",
                    f"{symbol} RSI at {rsi_val:.1f} indicates extreme overbought conditions.",
                    f"RSI above {RSI_EXTREME_OVERBOUGHT} points to an extended move and higher pullback risk.",
                    0.65,
                    SuggestedAction.SELL,
                    symbol=symbol,
                    evidence=[
                        {
                            "category": "technical",
                            "summary": "RSI value",
                            "value": round(float(rsi_val), 2),
                            "source": "technical_analysis",
                            "timestamp": _now_iso(),
                        }
                    ],
                    sources=["technical_analysis"],
                )
            )
        elif rsi_val >= RSI_OVERBOUGHT:
            alerts.append(
                _make_alert(
                    AlertType.TECHNICAL,
                    AlertSeverity.MEDIUM,
                    f"{symbol} overbought (RSI {rsi_val:.0f})",
                    f"{symbol} RSI at {rsi_val:.1f} is in overbought territory.",
                    f"RSI above {RSI_OVERBOUGHT} suggests recent upside may be stretched versus trend.",
                    0.55,
                    SuggestedAction.MONITOR,
                    symbol=symbol,
                    evidence=[
                        {
                            "category": "technical",
                            "summary": "RSI value",
                            "value": round(float(rsi_val), 2),
                            "source": "technical_analysis",
                            "timestamp": _now_iso(),
                        }
                    ],
                    sources=["technical_analysis"],
                )
            )

    counts = indicators.get("signal_counts", {})
    bullish_count = int(counts.get("bullish", 0) or 0)
    bearish_count = int(counts.get("bearish", 0) or 0)
    if bullish_count >= 4:
        alerts.append(
            _make_alert(
                AlertType.MULTI_FACTOR,
                AlertSeverity.HIGH,
                f"{symbol} strong bullish convergence",
                f"{symbol} shows {bullish_count}/5 bullish technical signals.",
                "Multiple independent technical signals are aligned bullish at the same time.",
                0.7 + min((bullish_count - 4) * 0.1, 0.15),
                SuggestedAction.BUY,
                symbol=symbol,
                evidence=[
                    {
                        "category": "technical",
                        "summary": "Bullish signal count",
                        "value": bullish_count,
                        "source": "technical_analysis",
                        "timestamp": _now_iso(),
                    }
                ],
                sources=["technical_analysis"],
            )
        )
    elif bearish_count >= 4:
        alerts.append(
            _make_alert(
                AlertType.MULTI_FACTOR,
                AlertSeverity.HIGH,
                f"{symbol} strong bearish convergence",
                f"{symbol} shows {bearish_count}/5 bearish technical signals.",
                "Multiple independent technical signals are aligned bearish at the same time.",
                0.7 + min((bearish_count - 4) * 0.1, 0.15),
                SuggestedAction.SELL,
                symbol=symbol,
                evidence=[
                    {
                        "category": "technical",
                        "summary": "Bearish signal count",
                        "value": bearish_count,
                        "source": "technical_analysis",
                        "timestamp": _now_iso(),
                    }
                ],
                sources=["technical_analysis"],
            )
        )

    return alerts


def _contextual_alerts(
    symbol: str,
    quote: dict | None,
    indicators: dict | None,
    sentiment: dict | None,
) -> list[StructuredAlert]:
    if not quote or not indicators or not sentiment:
        return []

    alerts: list[StructuredAlert] = []
    change_pct = float(quote.get("change_percent", 0.0) or 0.0)
    overall = str(indicators.get("overall_signal", "neutral")).lower()
    counts = indicators.get("signal_counts", {})
    bullish_count = int(counts.get("bullish", 0) or 0)
    bearish_count = int(counts.get("bearish", 0) or 0)
    sentiment_score = float(sentiment.get("unified_score", 0.0) or 0.0)
    coverage = float(sentiment.get("coverage_confidence", 0.0) or 0.0)
    recent_shift = float(sentiment.get("recent_shift", 0.0) or 0.0)
    warnings = list(sentiment.get("warnings", []) or [])
    sources = ["market_data", "technical_analysis", *_source_names(sentiment)]

    if change_pct >= 4.0 and overall == "bullish" and bullish_count >= 3 and sentiment_score >= 0.15:
        alerts.append(
            _make_alert(
                AlertType.MULTI_FACTOR,
                AlertSeverity.HIGH if change_pct >= 6.0 else AlertSeverity.MEDIUM,
                f"{symbol} bullish breakout backed by sentiment",
                f"{symbol} is moving higher with aligned technical and sentiment context.",
                "The move is supported by price strength, bullish technical posture, and positive multi-source sentiment instead of isolated noise.",
                _clip(0.58 + coverage * 0.2 + min(change_pct / 15.0, 0.18)),
                SuggestedAction.MONITOR,
                symbol=symbol,
                reason="Technical breakout is confirmed by sentiment context.",
                evidence=[
                    {"category": "price", "summary": "Daily move", "value": round(change_pct, 2), "source": "market_data", "timestamp": _now_iso()},
                    {"category": "technical", "summary": "Bullish technical count", "value": bullish_count, "source": "technical_analysis", "timestamp": _now_iso()},
                    {"category": "sentiment", "summary": "Unified sentiment score", "value": round(sentiment_score, 4), "source": "enhanced_sentiment", "timestamp": _now_iso()},
                ],
                sources=sources,
                warnings=warnings,
            )
        )
    elif change_pct <= -4.0 and overall == "bearish" and bearish_count >= 3 and sentiment_score <= -0.15:
        alerts.append(
            _make_alert(
                AlertType.MULTI_FACTOR,
                AlertSeverity.HIGH if change_pct <= -6.0 else AlertSeverity.MEDIUM,
                f"{symbol} bearish breakdown backed by sentiment",
                f"{symbol} is moving lower with aligned technical and sentiment deterioration.",
                "The downside move is being confirmed by both technical signals and negative sentiment flow.",
                _clip(0.58 + coverage * 0.2 + min(abs(change_pct) / 15.0, 0.18)),
                SuggestedAction.MONITOR,
                symbol=symbol,
                reason="Technical breakdown is confirmed by negative sentiment.",
                evidence=[
                    {"category": "price", "summary": "Daily move", "value": round(change_pct, 2), "source": "market_data", "timestamp": _now_iso()},
                    {"category": "technical", "summary": "Bearish technical count", "value": bearish_count, "source": "technical_analysis", "timestamp": _now_iso()},
                    {"category": "sentiment", "summary": "Unified sentiment score", "value": round(sentiment_score, 4), "source": "enhanced_sentiment", "timestamp": _now_iso()},
                ],
                sources=sources,
                warnings=warnings,
            )
        )

    if abs(recent_shift) >= 0.28 and coverage >= 0.15:
        direction = "bullish" if recent_shift > 0 else "bearish"
        alerts.append(
            _make_alert(
                AlertType.SENTIMENT,
                AlertSeverity.HIGH if abs(recent_shift) >= 0.5 and coverage >= 0.35 else AlertSeverity.MEDIUM,
                f"{symbol} sentiment shifted {direction}",
                f"Recent sentiment moved {recent_shift:+.2f} with coverage confidence {coverage:.2f}.",
                "Short-term sentiment has changed materially versus the recent baseline and may precede a positioning or narrative shift.",
                _clip(0.5 + coverage * 0.25 + min(abs(recent_shift), 0.25)),
                SuggestedAction.MONITOR,
                symbol=symbol,
                reason="Sentiment momentum changed materially over the recent window.",
                evidence=[
                    {"category": "sentiment", "summary": "Recent sentiment shift", "value": round(recent_shift, 4), "source": "enhanced_sentiment", "timestamp": _now_iso()},
                    {"category": "sentiment", "summary": "Coverage confidence", "value": round(coverage, 4), "source": "enhanced_sentiment", "timestamp": _now_iso()},
                ],
                sources=_source_names(sentiment) or ["enhanced_sentiment"],
                warnings=warnings,
            )
        )

    if (overall == "bullish" and sentiment_score <= -0.25) or (overall == "bearish" and sentiment_score >= 0.25):
        alerts.append(
            _make_alert(
                AlertType.SENTIMENT,
                AlertSeverity.MEDIUM,
                f"{symbol} has contradictory technical and sentiment signals",
                f"Technical posture is {overall} while structured sentiment is {_polarity(sentiment_score)}.",
                "Conflicting signals reduce conviction and increase the chance of false breakouts or abrupt reversals.",
                _clip(0.45 + coverage * 0.2),
                SuggestedAction.WAIT,
                symbol=symbol,
                reason="Technical and sentiment layers are pointing in opposite directions.",
                evidence=[
                    {"category": "technical", "summary": "Overall technical signal", "value": overall, "source": "technical_analysis", "timestamp": _now_iso()},
                    {"category": "sentiment", "summary": "Unified sentiment score", "value": round(sentiment_score, 4), "source": "enhanced_sentiment", "timestamp": _now_iso()},
                ],
                sources=sources,
                warnings=warnings + list(sentiment.get("divergences", [])[:2]),
            )
        )

    return alerts


def _polarity(value: float) -> str:
    if value >= 0.2:
        return "bullish"
    if value <= -0.2:
        return "bearish"
    return "neutral"


def _filing_alerts(symbol: str, filings: dict | None) -> list[StructuredAlert]:
    if not filings:
        return []
    filing_list = filings.get("filings", []) or []
    if not filing_list:
        return []

    latest = filing_list[0]
    form = str(latest.get("form") or "").upper()
    filed_at = str(latest.get("filed_at") or "")
    filed_dt = _parse_dt(filed_at)
    age_hours = (
        (datetime.now(timezone.utc) - filed_dt).total_seconds() / 3600.0
        if filed_dt is not None
        else 999.0
    )
    if age_hours > 96.0:
        return []

    severity = {
        "8-K": AlertSeverity.HIGH,
        "4": AlertSeverity.MEDIUM,
        "10-Q": AlertSeverity.MEDIUM,
        "10-K": AlertSeverity.MEDIUM,
        "6-K": AlertSeverity.MEDIUM,
        "20-F": AlertSeverity.MEDIUM,
        "S-1": AlertSeverity.HIGH,
    }.get(form, AlertSeverity.LOW)
    description = str(latest.get("description") or form or "Recent filing")
    items = str(latest.get("items") or "").strip()

    return [
        _make_alert(
            AlertType.MULTI_FACTOR,
            severity,
            f"{symbol} recent {form} filing needs review",
            f"{symbol} filed {form} recently: {description}",
            "Recent regulatory filings can materially change the information set even when price action has not reacted yet.",
            0.58 if form == "4" else 0.68,
            SuggestedAction.MONITOR,
            symbol=symbol,
            reason=f"Recent {form} filing may contain new material information.",
            evidence=[
                {"category": "filing", "summary": "Form type", "value": form, "source": "SEC EDGAR", "timestamp": filed_at or _now_iso()},
                {"category": "filing", "summary": "Description", "value": description[:120], "source": "SEC EDGAR", "timestamp": filed_at or _now_iso()},
                {"category": "filing", "summary": "Items", "value": items[:120], "source": "SEC EDGAR", "timestamp": filed_at or _now_iso()},
            ],
            sources=["SEC EDGAR"],
        )
    ]


def score_asset(
    symbol: str,
    quote: dict | None,
    indicators: dict | None,
    sentiment: dict | None = None,
    filings: dict | None = None,
) -> list[StructuredAlert]:
    alerts: list[StructuredAlert] = []
    if quote:
        alerts.extend(_price_move_alert(symbol, quote))
    if indicators:
        alerts.extend(_technical_alerts(symbol, indicators))
    alerts.extend(_contextual_alerts(symbol, quote, indicators, sentiment))
    alerts.extend(_filing_alerts(symbol, filings))

    deduped: dict[tuple[str, str | None], StructuredAlert] = {}
    for alert in alerts:
        key = (alert.title, alert.asset_symbol)
        if key not in deduped or alert.confidence > deduped[key].confidence:
            deduped[key] = alert
    return sort_alerts(list(deduped.values()))


async def _scan_single(item: dict) -> list[StructuredAlert]:
    symbol = item["symbol"].upper()
    asset_type = item.get("type")

    try:
        quote, history, sentiment, filings = await asyncio.gather(
            market_data_service.get_quote(symbol, asset_type),
            market_data_service.get_history(symbol, period="6mo", interval="1d"),
            get_enhanced_sentiment(symbol),
            get_company_filings(symbol, limit=4),
            return_exceptions=True,
        )

        quote_data = quote if isinstance(quote, dict) else None
        sentiment_data = sentiment if isinstance(sentiment, dict) else None
        filings_data = filings if isinstance(filings, dict) else None

        indicators = None
        if isinstance(history, list) and len(history) >= 30:
            closes = [r["close"] for r in history]
            indicators = compute_all_indicators(closes)

        return score_asset(symbol, quote_data, indicators, sentiment_data, filings_data)
    except Exception as exc:
        logger.warning("Alert scan failed for %s: %s", symbol, exc)
        return []


def sort_alerts(alerts: list[StructuredAlert]) -> list[StructuredAlert]:
    return sorted(
        alerts,
        key=lambda alert: (
            SEVERITY_ORDER.get(alert.severity, 99),
            -float(alert.confidence),
            alert.title,
        ),
    )


async def scan_symbols(symbols: list[dict]) -> list[StructuredAlert]:
    semaphore = asyncio.Semaphore(5)

    async def bounded_scan(item: dict) -> list[StructuredAlert]:
        async with semaphore:
            return await _scan_single(item)

    results = await asyncio.gather(
        *(bounded_scan(item) for item in symbols),
        return_exceptions=True,
    )

    all_alerts: list[StructuredAlert] = []
    for result in results:
        if isinstance(result, list):
            all_alerts.extend(result)
        elif isinstance(result, Exception):
            logger.warning("Parallel alert scan error: %s", result)
    return sort_alerts(all_alerts)


async def build_portfolio_alerts(holdings: list[dict]) -> list[StructuredAlert]:
    """Build portfolio-level alerts for concentration, macro stress, and allocation drift."""
    if not holdings:
        return []

    async def _enrich(holding: dict) -> dict | None:
        symbol = str(holding.get("symbol", "")).upper()
        if not symbol:
            return None
        quote = await market_data_service.get_quote(symbol, holding.get("type"))
        price = float((quote or {}).get("price") or holding.get("avg_buy_price", 0.0) or 0.0)
        current_value = price * float(holding.get("quantity", 0.0) or 0.0)
        if current_value <= 0:
            return None
        return {
            "symbol": symbol,
            "name": holding.get("name", symbol),
            "type": holding.get("type", "stock"),
            "quantity": float(holding.get("quantity", 0.0) or 0.0),
            "avg_buy_price": float(holding.get("avg_buy_price", 0.0) or 0.0),
            "current_value": current_value,
        }

    positions = [item for item in await asyncio.gather(*[_enrich(holding) for holding in holdings]) if item]
    if not positions:
        return []

    portfolio_intel, macro_indicators = await asyncio.gather(
        build_portfolio_intelligence(positions),
        get_all_macro_indicators(),
    )
    macro_summary = get_macro_summary(macro_indicators)

    alerts: list[StructuredAlert] = []
    concentration = portfolio_intel.get("concentration", {})
    allocation = portfolio_intel.get("allocation", [])
    equal_weight = next(
        (snapshot for snapshot in portfolio_intel.get("strategy_snapshots", []) if snapshot.get("name") == "equal_weight"),
        None,
    )
    equal_weight_map = {
        item["symbol"]: float(item.get("weight", 0.0) or 0.0)
        for item in (equal_weight or {}).get("target_weights", [])
    }

    asset_conc = concentration.get("asset", {})
    top_asset = asset_conc.get("items", [{}])[0] if asset_conc.get("items") else {}
    if float(top_asset.get("weight", 0.0) or 0.0) >= 0.25:
        alerts.append(
            _make_alert(
                AlertType.MULTI_FACTOR,
                AlertSeverity.HIGH if float(top_asset.get("weight", 0.0) or 0.0) >= 0.35 else AlertSeverity.MEDIUM,
                f"Portfolio concentration elevated in {top_asset.get('key', 'single position')}",
                f"{top_asset.get('key', 'A position')} represents {float(top_asset.get('weight', 0.0) or 0.0) * 100:.1f}% of portfolio value.",
                "Single-name concentration increases idiosyncratic risk and can dominate portfolio outcomes.",
                _clip(0.62 + float(top_asset.get("weight", 0.0) or 0.0)),
                SuggestedAction.MONITOR,
                reason="A single position has become a large share of total capital.",
                evidence=[
                    {
                        "category": "portfolio",
                        "summary": "Asset concentration",
                        "value": round(float(top_asset.get("weight", 0.0) or 0.0), 4),
                        "source": "portfolio_intelligence",
                        "timestamp": portfolio_intel.get("generated_at", _now_iso()),
                    }
                ],
                sources=["portfolio_intelligence"],
                warnings=portfolio_intel.get("warnings", []),
            )
        )

    sector_conc = concentration.get("sector", {})
    top_sector = sector_conc.get("items", [{}])[0] if sector_conc.get("items") else {}
    if float(top_sector.get("weight", 0.0) or 0.0) >= 0.40:
        alerts.append(
            _make_alert(
                AlertType.MULTI_FACTOR,
                AlertSeverity.MEDIUM,
                f"Sector concentration elevated in {top_sector.get('key', 'one sector')}",
                f"{top_sector.get('key', 'A sector')} is {float(top_sector.get('weight', 0.0) or 0.0) * 100:.1f}% of current exposure.",
                "High sector concentration weakens diversification and can amplify regime-specific drawdowns.",
                _clip(0.56 + float(top_sector.get("weight", 0.0) or 0.0) * 0.5),
                SuggestedAction.MONITOR,
                reason="Sector exposure is materially concentrated.",
                evidence=[
                    {
                        "category": "portfolio",
                        "summary": "Sector concentration",
                        "value": round(float(top_sector.get("weight", 0.0) or 0.0), 4),
                        "source": "portfolio_intelligence",
                        "timestamp": portfolio_intel.get("generated_at", _now_iso()),
                    }
                ],
                sources=["portfolio_intelligence"],
                warnings=portfolio_intel.get("warnings", []),
            )
        )

    if equal_weight_map:
        deviations = []
        for item in allocation:
            symbol = item.get("symbol")
            current = float(item.get("weight", 0.0) or 0.0)
            target = float(equal_weight_map.get(symbol, 0.0) or 0.0)
            deviation = current - target
            if deviation >= 0.15:
                deviations.append((symbol, deviation, current, target))
        deviations.sort(key=lambda entry: entry[1], reverse=True)
        if deviations:
            symbol, deviation, current, target = deviations[0]
            alerts.append(
                _make_alert(
                    AlertType.MULTI_FACTOR,
                    AlertSeverity.MEDIUM,
                    f"Allocation drift versus equal-weight reference in {symbol}",
                    f"{symbol} is {current * 100:.1f}% of the portfolio versus an equal-weight reference of {target * 100:.1f}%.",
                    "The current sizing has drifted materially above a simple diversification reference and may merit a rebalance review.",
                    _clip(0.5 + deviation),
                    SuggestedAction.MONITOR,
                    symbol=symbol,
                    reason="Position weight has drifted materially above an equal-weight reference.",
                    evidence=[
                        {"category": "portfolio", "summary": "Current weight", "value": round(current, 4), "source": "portfolio_intelligence", "timestamp": portfolio_intel.get("generated_at", _now_iso())},
                        {"category": "portfolio", "summary": "Equal-weight reference", "value": round(target, 4), "source": "portfolio_intelligence", "timestamp": portfolio_intel.get("generated_at", _now_iso())},
                    ],
                    sources=["portfolio_intelligence"],
                )
            )

    if macro_summary.get("environment") == "risk-off" and (
        float(top_asset.get("weight", 0.0) or 0.0) >= 0.20 or float(top_sector.get("weight", 0.0) or 0.0) >= 0.35
    ):
        alerts.append(
            _make_alert(
                AlertType.MACRO,
                AlertSeverity.HIGH,
                "Macro regime deteriorated while portfolio exposure remains concentrated",
                f"Macro summary is {macro_summary.get('environment', 'unknown')} with portfolio concentration still elevated.",
                "A more defensive macro backdrop matters more when exposure is concentrated in a few holdings or sectors.",
                0.72,
                SuggestedAction.MONITOR,
                reason="Macro deterioration and concentrated exposure are interacting.",
                evidence=[
                    {"category": "macro", "summary": "Macro environment", "value": macro_summary.get("environment", "unknown"), "source": "macro_intelligence", "timestamp": _now_iso()},
                    {"category": "portfolio", "summary": "Top asset weight", "value": round(float(top_asset.get("weight", 0.0) or 0.0), 4), "source": "portfolio_intelligence", "timestamp": portfolio_intel.get("generated_at", _now_iso())},
                    {"category": "portfolio", "summary": "Top sector weight", "value": round(float(top_sector.get("weight", 0.0) or 0.0), 4), "source": "portfolio_intelligence", "timestamp": portfolio_intel.get("generated_at", _now_iso())},
                ],
                sources=["macro_intelligence", "portfolio_intelligence"],
                warnings=portfolio_intel.get("warnings", []),
            )
        )

    correlation = portfolio_intel.get("correlation", {})
    high_corr = correlation.get("high_correlations", [])
    if high_corr:
        pair = high_corr[0]
        alerts.append(
            _make_alert(
                AlertType.MULTI_FACTOR,
                AlertSeverity.MEDIUM,
                f"High correlation cluster detected in {pair.get('pair', 'portfolio')}",
                f"Observed pairwise correlation is {float(pair.get('value', 0.0) or 0.0):.2f}.",
                "Highly correlated holdings often behave like one position during stress and reduce real diversification.",
                0.58,
                SuggestedAction.MONITOR,
                reason="Diversification benefit is weaker than nominal position count suggests.",
                evidence=[
                    {
                        "category": "portfolio",
                        "summary": "High pairwise correlation",
                        "value": round(float(pair.get("value", 0.0) or 0.0), 4),
                        "source": "portfolio_intelligence",
                        "timestamp": portfolio_intel.get("generated_at", _now_iso()),
                    }
                ],
                sources=["portfolio_intelligence"],
            )
        )

    return sort_alerts(alerts)
