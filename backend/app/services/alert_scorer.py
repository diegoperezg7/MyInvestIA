"""Alert scoring service that generates multi-factor alerts.

Analyzes assets using technical indicators, price movements, and volume
to produce actionable alerts with severity, reasoning, and suggested actions.
Runs on-demand against portfolio holdings and watchlist assets.
"""

import logging
import uuid
from datetime import datetime, timezone

from app.schemas.asset import (
    Alert,
    AlertSeverity,
    AlertType,
    SuggestedAction,
)
from app.services.market_data import market_data_service
from app.services.technical_analysis import compute_all_indicators

logger = logging.getLogger(__name__)

# Thresholds for alert generation
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
RSI_EXTREME_OVERSOLD = 20
RSI_EXTREME_OVERBOUGHT = 80
PRICE_SPIKE_THRESHOLD = 5.0  # percent
PRICE_DROP_THRESHOLD = -5.0  # percent


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_alert(
    alert_type: AlertType,
    severity: AlertSeverity,
    title: str,
    description: str,
    reasoning: str,
    confidence: float,
    action: SuggestedAction,
    symbol: str | None = None,
) -> Alert:
    return Alert(
        id=str(uuid.uuid4()),
        type=alert_type,
        severity=severity,
        title=title,
        description=description,
        reasoning=reasoning,
        confidence=round(min(max(confidence, 0.0), 1.0), 2),
        suggested_action=action,
        created_at=_now_iso(),
        asset_symbol=symbol,
    )


def score_asset(symbol: str, quote: dict | None, indicators: dict | None) -> list[Alert]:
    """Generate alerts for a single asset based on its quote and technical indicators.

    Args:
        symbol: Asset ticker
        quote: Quote dict with price, change_percent, volume
        indicators: Result from compute_all_indicators()

    Returns:
        List of Alert objects (may be empty if no notable conditions detected)
    """
    alerts: list[Alert] = []

    # --- Price movement alerts ---
    if quote:
        change_pct = quote.get("change_percent", 0.0)

        if change_pct >= PRICE_SPIKE_THRESHOLD:
            severity = AlertSeverity.HIGH if change_pct >= 8.0 else AlertSeverity.MEDIUM
            alerts.append(_make_alert(
                alert_type=AlertType.PRICE,
                severity=severity,
                title=f"{symbol} surging +{change_pct:.1f}%",
                description=f"{symbol} is up {change_pct:.1f}% today with significant upward momentum.",
                reasoning=f"Price has moved +{change_pct:.1f}% which exceeds the {PRICE_SPIKE_THRESHOLD}% threshold. Large single-day moves often indicate a catalyst or momentum shift.",
                confidence=min(0.5 + abs(change_pct) / 20.0, 0.9),
                action=SuggestedAction.MONITOR,
                symbol=symbol,
            ))

        elif change_pct <= PRICE_DROP_THRESHOLD:
            severity = AlertSeverity.HIGH if change_pct <= -8.0 else AlertSeverity.MEDIUM
            alerts.append(_make_alert(
                alert_type=AlertType.PRICE,
                severity=severity,
                title=f"{symbol} dropping {change_pct:.1f}%",
                description=f"{symbol} is down {change_pct:.1f}% today with significant selling pressure.",
                reasoning=f"Price has moved {change_pct:.1f}% which exceeds the {PRICE_DROP_THRESHOLD}% threshold. Sharp drops may present buying opportunities or signal deeper problems.",
                confidence=min(0.5 + abs(change_pct) / 20.0, 0.9),
                action=SuggestedAction.MONITOR,
                symbol=symbol,
            ))

    # --- Technical indicator alerts ---
    if indicators:
        rsi_data = indicators.get("rsi", {})
        rsi_val = rsi_data.get("value")

        if rsi_val is not None:
            if rsi_val <= RSI_EXTREME_OVERSOLD:
                alerts.append(_make_alert(
                    alert_type=AlertType.TECHNICAL,
                    severity=AlertSeverity.HIGH,
                    title=f"{symbol} extremely oversold (RSI {rsi_val:.0f})",
                    description=f"{symbol} RSI at {rsi_val:.1f} indicates extreme oversold conditions. Historically, this often precedes a bounce.",
                    reasoning=f"RSI below {RSI_EXTREME_OVERSOLD} suggests extreme selling exhaustion. While this could continue in a strong downtrend, mean reversion is statistically likely.",
                    confidence=0.65,
                    action=SuggestedAction.BUY,
                    symbol=symbol,
                ))
            elif rsi_val <= RSI_OVERSOLD:
                alerts.append(_make_alert(
                    alert_type=AlertType.TECHNICAL,
                    severity=AlertSeverity.MEDIUM,
                    title=f"{symbol} oversold (RSI {rsi_val:.0f})",
                    description=f"{symbol} RSI at {rsi_val:.1f} is in oversold territory, suggesting potential buying opportunity.",
                    reasoning=f"RSI below {RSI_OVERSOLD} indicates the asset may be undervalued relative to recent price action.",
                    confidence=0.55,
                    action=SuggestedAction.MONITOR,
                    symbol=symbol,
                ))
            elif rsi_val >= RSI_EXTREME_OVERBOUGHT:
                alerts.append(_make_alert(
                    alert_type=AlertType.TECHNICAL,
                    severity=AlertSeverity.HIGH,
                    title=f"{symbol} extremely overbought (RSI {rsi_val:.0f})",
                    description=f"{symbol} RSI at {rsi_val:.1f} indicates extreme overbought conditions. A pullback is increasingly likely.",
                    reasoning=f"RSI above {RSI_EXTREME_OVERBOUGHT} suggests buying exhaustion. This often precedes a correction or consolidation.",
                    confidence=0.65,
                    action=SuggestedAction.SELL,
                    symbol=symbol,
                ))
            elif rsi_val >= RSI_OVERBOUGHT:
                alerts.append(_make_alert(
                    alert_type=AlertType.TECHNICAL,
                    severity=AlertSeverity.MEDIUM,
                    title=f"{symbol} overbought (RSI {rsi_val:.0f})",
                    description=f"{symbol} RSI at {rsi_val:.1f} is in overbought territory. Consider taking profits or tightening stops.",
                    reasoning=f"RSI above {RSI_OVERBOUGHT} suggests the asset may be overextended relative to recent price action.",
                    confidence=0.55,
                    action=SuggestedAction.MONITOR,
                    symbol=symbol,
                ))

        # MACD crossover signals
        macd_data = indicators.get("macd", {})
        macd_signal = macd_data.get("signal", "neutral")
        macd_hist = macd_data.get("histogram")

        if macd_hist is not None and abs(macd_hist) > 0:
            # Strong bullish or bearish MACD with supporting signals
            overall = indicators.get("overall_signal", "neutral")
            counts = indicators.get("signal_counts", {})
            bullish_count = counts.get("bullish", 0)
            bearish_count = counts.get("bearish", 0)

            if bullish_count >= 4:
                alerts.append(_make_alert(
                    alert_type=AlertType.MULTI_FACTOR,
                    severity=AlertSeverity.HIGH,
                    title=f"{symbol} strong bullish convergence",
                    description=f"{symbol} shows {bullish_count}/5 bullish signals across RSI, MACD, SMA, EMA, and Bollinger Bands.",
                    reasoning=f"Multiple technical indicators aligning bullish simultaneously suggests strong upward momentum. This multi-factor confirmation increases signal reliability.",
                    confidence=0.7 + (bullish_count - 4) * 0.1,
                    action=SuggestedAction.BUY,
                    symbol=symbol,
                ))
            elif bearish_count >= 4:
                alerts.append(_make_alert(
                    alert_type=AlertType.MULTI_FACTOR,
                    severity=AlertSeverity.HIGH,
                    title=f"{symbol} strong bearish convergence",
                    description=f"{symbol} shows {bearish_count}/5 bearish signals across RSI, MACD, SMA, EMA, and Bollinger Bands.",
                    reasoning=f"Multiple technical indicators aligning bearish simultaneously suggests strong downward pressure. This multi-factor confirmation increases signal reliability.",
                    confidence=0.7 + (bearish_count - 4) * 0.1,
                    action=SuggestedAction.SELL,
                    symbol=symbol,
                ))

    return alerts


async def scan_symbols(symbols: list[dict]) -> list[Alert]:
    """Scan a list of symbols and generate alerts for any notable conditions.

    Args:
        symbols: List of {"symbol": str, "type": str} dicts

    Returns:
        List of alerts sorted by severity (critical first)
    """
    all_alerts: list[Alert] = []

    for item in symbols:
        symbol = item["symbol"].upper()
        asset_type = item.get("type")

        try:
            # Get quote
            quote = await market_data_service.get_quote(symbol, asset_type)

            # Get technical indicators
            indicators = None
            history = market_data_service.get_history(symbol, period="6mo", interval="1d")
            if history and len(history) >= 30:
                closes = [r["close"] for r in history]
                indicators = compute_all_indicators(closes)

            alerts = score_asset(symbol, quote, indicators)
            all_alerts.extend(alerts)

        except Exception as e:
            logger.warning("Alert scan failed for %s: %s", symbol, e)

    # Sort: critical > high > medium > low
    severity_order = {
        AlertSeverity.CRITICAL: 0,
        AlertSeverity.HIGH: 1,
        AlertSeverity.MEDIUM: 2,
        AlertSeverity.LOW: 3,
    }
    all_alerts.sort(key=lambda a: severity_order.get(a.severity, 99))

    return all_alerts
