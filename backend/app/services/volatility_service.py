"""Volatility analysis service.

Computes Historical Volatility, ATR, RSI, Bollinger Bandwidth,
daily/weekly ranges, and an overall volatility rating.
"""

import math
import logging

import numpy as np

from app.services.technical_analysis import rsi as calc_rsi, bollinger_bands

logger = logging.getLogger(__name__)


def compute_volatility(symbol: str, records: list[dict], current_price: float) -> dict:
    """Compute volatility metrics from historical OHLCV data.

    Args:
        symbol: Asset ticker
        records: List of OHLCV dicts from get_history()
        current_price: Current market price

    Returns:
        Dict with volatility metrics and rating
    """
    closes = [r["close"] for r in records]
    highs = [r["high"] for r in records]
    lows = [r["low"] for r in records]

    # Historical Volatility (annualized std dev of log returns)
    log_returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0:
            log_returns.append(math.log(closes[i] / closes[i - 1]))

    hv = float(np.std(log_returns) * math.sqrt(252)) if log_returns else 0.0

    # ATR (Average True Range, 14-period)
    atr = _compute_atr(highs, lows, closes, period=14)
    atr_percent = (atr / current_price * 100) if current_price else 0.0

    # RSI
    rsi_values = calc_rsi(closes)
    latest_rsi = next((v for v in reversed(rsi_values) if v is not None), 50.0)

    # Bollinger Bandwidth
    bb = bollinger_bands(closes)
    latest_bw = next((v for v in reversed(bb["bandwidth"]) if v is not None), 0.0)

    # Daily range (latest day)
    daily_high = records[-1]["high"] if records else current_price
    daily_low = records[-1]["low"] if records else current_price
    daily_range_pct = ((daily_high - daily_low) / daily_low * 100) if daily_low else 0

    # Weekly range (last 5 trading days)
    week_data = records[-5:] if len(records) >= 5 else records
    weekly_high = max(r["high"] for r in week_data)
    weekly_low = min(r["low"] for r in week_data)
    weekly_range_pct = ((weekly_high - weekly_low) / weekly_low * 100) if weekly_low else 0

    # Volatility rating
    rating = _rate_volatility(hv, atr_percent, latest_bw)

    return {
        "symbol": symbol,
        "historical_volatility": round(hv, 4),
        "atr": round(atr, 4),
        "atr_percent": round(atr_percent, 2),
        "rsi": round(latest_rsi, 2),
        "bollinger_bandwidth": round(latest_bw, 2),
        "daily_range": {
            "high": round(daily_high, 2),
            "low": round(daily_low, 2),
            "range_percent": round(daily_range_pct, 2),
        },
        "weekly_range": {
            "high": round(weekly_high, 2),
            "low": round(weekly_low, 2),
            "range_percent": round(weekly_range_pct, 2),
        },
        "current_price": round(current_price, 2),
        "volatility_rating": rating,
    }


def _compute_atr(highs: list, lows: list, closes: list, period: int = 14) -> float:
    """Average True Range calculation."""
    if len(closes) < period + 1:
        return 0.0

    true_ranges = []
    for i in range(1, len(closes)):
        high_low = highs[i] - lows[i]
        high_close = abs(highs[i] - closes[i - 1])
        low_close = abs(lows[i] - closes[i - 1])
        true_ranges.append(max(high_low, high_close, low_close))

    if len(true_ranges) < period:
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0

    # Simple average of last `period` true ranges
    return sum(true_ranges[-period:]) / period


def _rate_volatility(hv: float, atr_pct: float, bb_width: float) -> str:
    """Rate volatility as low, moderate, high, or extreme."""
    score = 0

    if hv > 0.6:
        score += 3
    elif hv > 0.4:
        score += 2
    elif hv > 0.2:
        score += 1

    if atr_pct > 4:
        score += 3
    elif atr_pct > 2.5:
        score += 2
    elif atr_pct > 1.5:
        score += 1

    if bb_width > 15:
        score += 2
    elif bb_width > 8:
        score += 1

    if score >= 6:
        return "extreme"
    elif score >= 4:
        return "high"
    elif score >= 2:
        return "moderate"
    return "low"
