"""Aggregate oscillators + moving averages into BUY/SELL/NEUTRAL ratings.

Follows the tvscreener pattern of separating indicators into:
- Oscillators: RSI, MACD, Stochastic, CCI, ADX
- Moving Averages: SMA 20, SMA 50, EMA 12, EMA 26
"""

import logging

from app.schemas.signals import SignalDirection, SignalSummary, StructuredSignal
from app.services.rule_engine import generate_rule_signals

logger = logging.getLogger(__name__)


def _direction_to_category(d: SignalDirection) -> str:
    """Map direction to buy/sell/neutral category."""
    if d in (SignalDirection.STRONG_BUY, SignalDirection.BUY):
        return "buy"
    elif d in (SignalDirection.STRONG_SELL, SignalDirection.SELL):
        return "sell"
    return "neutral"


def _aggregate_direction(buy: int, sell: int, total: int) -> SignalDirection:
    """Determine overall direction from counts."""
    if total == 0:
        return SignalDirection.NEUTRAL
    buy_ratio = buy / total
    sell_ratio = sell / total

    if buy_ratio >= 0.7:
        return SignalDirection.STRONG_BUY
    elif buy_ratio > sell_ratio and buy > sell:
        return SignalDirection.BUY
    elif sell_ratio >= 0.7:
        return SignalDirection.STRONG_SELL
    elif sell_ratio > buy_ratio and sell > buy:
        return SignalDirection.SELL
    return SignalDirection.NEUTRAL


OSCILLATOR_SOURCES = {"RSI", "MACD", "Stochastic", "CCI", "ADX"}
MA_SOURCES = {"SMA Cross", "EMA Cross", "SMA 10", "SMA 20", "SMA 50", "SMA 100", "SMA 200",
              "EMA 10", "EMA 20", "EMA 50", "EMA 100", "EMA 200"}


def build_signal_summary(
    symbol: str,
    indicators: dict,
    price: float | None = None,
) -> SignalSummary:
    """Build a complete signal summary from technical indicators.

    Args:
        symbol: Asset symbol
        indicators: Result from compute_all_indicators() or extended version
        price: Current price

    Returns:
        SignalSummary with oscillator and MA breakdowns
    """
    signals = generate_rule_signals(indicators, price)

    # Classify signals
    osc_buy = osc_sell = osc_neutral = 0
    ma_buy = ma_sell = ma_neutral = 0

    for sig in signals:
        cat = _direction_to_category(sig.direction)
        if sig.source in OSCILLATOR_SOURCES or sig.source in ("RSI", "MACD"):
            if cat == "buy":
                osc_buy += 1
            elif cat == "sell":
                osc_sell += 1
            else:
                osc_neutral += 1
        else:
            if cat == "buy":
                ma_buy += 1
            elif cat == "sell":
                ma_sell += 1
            else:
                ma_neutral += 1

    osc_total = osc_buy + osc_sell + osc_neutral
    ma_total = ma_buy + ma_sell + ma_neutral
    total = osc_total + ma_total

    osc_rating = _aggregate_direction(osc_buy, osc_sell, osc_total)
    ma_rating = _aggregate_direction(ma_buy, ma_sell, ma_total)

    total_buy = osc_buy + ma_buy
    total_sell = osc_sell + ma_sell
    overall = _aggregate_direction(total_buy, total_sell, total)

    # Confidence: weighted average of signal confidences
    if signals:
        overall_confidence = sum(s.confidence for s in signals) / len(signals)
    else:
        overall_confidence = 50.0

    return SignalSummary(
        symbol=symbol.upper(),
        overall=overall,
        overall_confidence=round(overall_confidence, 1),
        oscillators_rating=osc_rating,
        oscillators_buy=osc_buy,
        oscillators_sell=osc_sell,
        oscillators_neutral=osc_neutral,
        moving_averages_rating=ma_rating,
        moving_averages_buy=ma_buy,
        moving_averages_sell=ma_sell,
        moving_averages_neutral=ma_neutral,
        signals=signals,
    )
