"""Rule-based signal generator from technical indicators.

Provides BUY/SELL/HOLD signals when AI is unavailable.
Uses a configurable set of rules based on RSI, MACD, SMA, EMA, and Bollinger Bands.
"""

import logging

from app.schemas.signals import SignalDirection, StructuredSignal

logger = logging.getLogger(__name__)


def generate_rule_signals(indicators: dict, price: float | None = None) -> list[StructuredSignal]:
    """Generate structured signals from technical indicators using rules.

    Args:
        indicators: Result from compute_all_indicators()
        price: Current price (optional, used for some rules)

    Returns:
        List of StructuredSignal objects
    """
    signals: list[StructuredSignal] = []

    # --- RSI Rules ---
    rsi_data = indicators.get("rsi", {})
    rsi_val = rsi_data.get("value")
    if rsi_val is not None:
        if rsi_val <= 20:
            signals.append(StructuredSignal(
                direction=SignalDirection.STRONG_BUY,
                confidence=80.0,
                source="RSI",
                reasoning=f"RSI at {rsi_val:.1f} - extremely oversold, high probability of bounce",
            ))
        elif rsi_val <= 30:
            signals.append(StructuredSignal(
                direction=SignalDirection.BUY,
                confidence=65.0,
                source="RSI",
                reasoning=f"RSI at {rsi_val:.1f} - oversold conditions",
            ))
        elif rsi_val >= 80:
            signals.append(StructuredSignal(
                direction=SignalDirection.STRONG_SELL,
                confidence=80.0,
                source="RSI",
                reasoning=f"RSI at {rsi_val:.1f} - extremely overbought, pullback likely",
            ))
        elif rsi_val >= 70:
            signals.append(StructuredSignal(
                direction=SignalDirection.SELL,
                confidence=65.0,
                source="RSI",
                reasoning=f"RSI at {rsi_val:.1f} - overbought conditions",
            ))
        else:
            signals.append(StructuredSignal(
                direction=SignalDirection.NEUTRAL,
                confidence=50.0,
                source="RSI",
                reasoning=f"RSI at {rsi_val:.1f} - neutral range",
            ))

    # --- MACD Rules ---
    macd_data = indicators.get("macd", {})
    macd_line = macd_data.get("macd_line")
    signal_line = macd_data.get("signal_line")
    histogram = macd_data.get("histogram")

    if macd_line is not None and signal_line is not None:
        if histogram is not None and histogram > 0 and macd_line > signal_line:
            confidence = min(60.0 + abs(histogram) * 100, 85.0)
            signals.append(StructuredSignal(
                direction=SignalDirection.BUY,
                confidence=confidence,
                source="MACD",
                reasoning=f"MACD bullish crossover, histogram {histogram:.4f}",
            ))
        elif histogram is not None and histogram < 0 and macd_line < signal_line:
            confidence = min(60.0 + abs(histogram) * 100, 85.0)
            signals.append(StructuredSignal(
                direction=SignalDirection.SELL,
                confidence=confidence,
                source="MACD",
                reasoning=f"MACD bearish crossover, histogram {histogram:.4f}",
            ))
        else:
            signals.append(StructuredSignal(
                direction=SignalDirection.NEUTRAL,
                confidence=50.0,
                source="MACD",
                reasoning="MACD in transition",
            ))

    # --- SMA Rules ---
    sma_data = indicators.get("sma", {})
    sma_20 = sma_data.get("sma_20")
    sma_50 = sma_data.get("sma_50")
    if sma_20 is not None and sma_50 is not None:
        if sma_20 > sma_50:
            gap_pct = ((sma_20 - sma_50) / sma_50) * 100 if sma_50 else 0
            signals.append(StructuredSignal(
                direction=SignalDirection.BUY,
                confidence=min(60.0 + gap_pct * 5, 80.0),
                source="SMA Cross",
                reasoning=f"SMA 20 ({sma_20:.2f}) above SMA 50 ({sma_50:.2f}) - golden cross",
            ))
        else:
            gap_pct = ((sma_50 - sma_20) / sma_50) * 100 if sma_50 else 0
            signals.append(StructuredSignal(
                direction=SignalDirection.SELL,
                confidence=min(60.0 + gap_pct * 5, 80.0),
                source="SMA Cross",
                reasoning=f"SMA 20 ({sma_20:.2f}) below SMA 50 ({sma_50:.2f}) - death cross",
            ))

    # --- EMA Rules ---
    ema_data = indicators.get("ema", {})
    ema_12 = ema_data.get("ema_12")
    ema_26 = ema_data.get("ema_26")
    if ema_12 is not None and ema_26 is not None:
        if ema_12 > ema_26:
            signals.append(StructuredSignal(
                direction=SignalDirection.BUY,
                confidence=62.0,
                source="EMA Cross",
                reasoning=f"EMA 12 ({ema_12:.2f}) above EMA 26 ({ema_26:.2f})",
            ))
        else:
            signals.append(StructuredSignal(
                direction=SignalDirection.SELL,
                confidence=62.0,
                source="EMA Cross",
                reasoning=f"EMA 12 ({ema_12:.2f}) below EMA 26 ({ema_26:.2f})",
            ))

    # --- Bollinger Band Rules ---
    bb_data = indicators.get("bollinger_bands", {})
    bb_upper = bb_data.get("upper")
    bb_lower = bb_data.get("lower")
    if price is not None and bb_upper is not None and bb_lower is not None:
        if price <= bb_lower:
            signals.append(StructuredSignal(
                direction=SignalDirection.BUY,
                confidence=68.0,
                source="Bollinger Bands",
                reasoning=f"Price (${price:.2f}) at lower band (${bb_lower:.2f}) - potential bounce",
            ))
        elif price >= bb_upper:
            signals.append(StructuredSignal(
                direction=SignalDirection.SELL,
                confidence=68.0,
                source="Bollinger Bands",
                reasoning=f"Price (${price:.2f}) at upper band (${bb_upper:.2f}) - potential pullback",
            ))
        else:
            signals.append(StructuredSignal(
                direction=SignalDirection.NEUTRAL,
                confidence=50.0,
                source="Bollinger Bands",
                reasoning="Price within Bollinger Bands range",
            ))

    return signals
