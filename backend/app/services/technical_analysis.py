"""Technical analysis service computing indicators from historical price data.

Implements RSI, MACD, EMA, SMA, and Bollinger Bands using numpy for performance.
All functions accept a list of close prices (floats) and return computed values.
"""

import numpy as np


def sma(closes: list[float], period: int = 20) -> list[float | None]:
    """Simple Moving Average.

    Returns list same length as input, with None for insufficient data points.
    """
    if len(closes) < period:
        return [None] * len(closes)

    arr = np.array(closes, dtype=float)
    kernel = np.ones(period) / period
    conv = np.convolve(arr, kernel, mode="valid")

    result: list[float | None] = [None] * (period - 1)
    result.extend(round(float(v), 4) for v in conv)
    return result


def ema(closes: list[float], period: int = 20) -> list[float | None]:
    """Exponential Moving Average.

    Uses standard EMA formula: multiplier = 2 / (period + 1).
    """
    if len(closes) < period:
        return [None] * len(closes)

    arr = np.array(closes, dtype=float)
    multiplier = 2.0 / (period + 1)

    # Seed with SMA of first `period` values
    ema_values = np.empty(len(arr))
    ema_values[:period - 1] = np.nan
    ema_values[period - 1] = np.mean(arr[:period])

    for i in range(period, len(arr)):
        ema_values[i] = arr[i] * multiplier + ema_values[i - 1] * (1 - multiplier)

    result: list[float | None] = []
    for v in ema_values:
        result.append(round(float(v), 4) if not np.isnan(v) else None)
    return result


def rsi(closes: list[float], period: int = 14) -> list[float | None]:
    """Relative Strength Index (0-100).

    Uses Wilder's smoothing method (exponential moving average of gains/losses).
    """
    if len(closes) < period + 1:
        return [None] * len(closes)

    arr = np.array(closes, dtype=float)
    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    result: list[float | None] = [None] * period

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(round(100.0 - (100.0 / (1.0 + rs)), 2))

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(round(100.0 - (100.0 / (1.0 + rs)), 2))

    return result


def macd(
    closes: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> dict[str, list[float | None]]:
    """Moving Average Convergence Divergence.

    Returns dict with:
        macd_line: fast EMA - slow EMA
        signal_line: EMA of MACD line
        histogram: MACD - signal
    """
    n = len(closes)
    if n < slow_period:
        return {
            "macd_line": [None] * n,
            "signal_line": [None] * n,
            "histogram": [None] * n,
        }

    fast_ema = ema(closes, fast_period)
    slow_ema = ema(closes, slow_period)

    # MACD line = fast EMA - slow EMA
    macd_line: list[float | None] = []
    macd_raw: list[float] = []
    for f, s in zip(fast_ema, slow_ema):
        if f is not None and s is not None:
            val = round(f - s, 4)
            macd_line.append(val)
            macd_raw.append(val)
        else:
            macd_line.append(None)

    # Signal line = EMA of MACD values
    if len(macd_raw) >= signal_period:
        signal_vals = ema(macd_raw, signal_period)
    else:
        signal_vals = [None] * len(macd_raw)

    # Reconstruct full-length signal line
    signal_line: list[float | None] = [None] * (n - len(signal_vals))
    signal_line.extend(signal_vals)

    # Histogram = MACD - Signal
    histogram: list[float | None] = []
    for m, s in zip(macd_line, signal_line):
        if m is not None and s is not None:
            histogram.append(round(m - s, 4))
        else:
            histogram.append(None)

    return {
        "macd_line": macd_line,
        "signal_line": signal_line,
        "histogram": histogram,
    }


def bollinger_bands(
    closes: list[float],
    period: int = 20,
    std_dev: float = 2.0,
) -> dict[str, list[float | None]]:
    """Bollinger Bands.

    Returns dict with:
        upper: SMA + std_dev * stddev
        middle: SMA
        lower: SMA - std_dev * stddev
        bandwidth: (upper - lower) / middle * 100
    """
    n = len(closes)
    if n < period:
        return {
            "upper": [None] * n,
            "middle": [None] * n,
            "lower": [None] * n,
            "bandwidth": [None] * n,
        }

    middle = sma(closes, period)
    arr = np.array(closes, dtype=float)

    upper: list[float | None] = [None] * (period - 1)
    lower: list[float | None] = [None] * (period - 1)
    bandwidth: list[float | None] = [None] * (period - 1)

    for i in range(period - 1, n):
        window = arr[i - period + 1: i + 1]
        sd = float(np.std(window, ddof=0))
        mid = middle[i]
        if mid is not None:
            u = round(mid + std_dev * sd, 4)
            lo = round(mid - std_dev * sd, 4)
            bw = round((u - lo) / mid * 100, 4) if mid != 0 else 0.0
            upper.append(u)
            lower.append(lo)
            bandwidth.append(bw)
        else:
            upper.append(None)
            lower.append(None)
            bandwidth.append(None)

    return {
        "upper": upper,
        "middle": middle,
        "lower": lower,
        "bandwidth": bandwidth,
    }


def compute_all_indicators(closes: list[float]) -> dict:
    """Compute all technical indicators for a price series.

    Returns the latest value of each indicator plus overall signal assessment.
    """
    result: dict = {}

    # RSI
    rsi_values = rsi(closes)
    latest_rsi = next((v for v in reversed(rsi_values) if v is not None), None)
    result["rsi"] = {
        "value": latest_rsi,
        "signal": _rsi_signal(latest_rsi),
    }

    # MACD
    macd_data = macd(closes)
    latest_macd = next((v for v in reversed(macd_data["macd_line"]) if v is not None), None)
    latest_signal = next((v for v in reversed(macd_data["signal_line"]) if v is not None), None)
    latest_hist = next((v for v in reversed(macd_data["histogram"]) if v is not None), None)
    result["macd"] = {
        "macd_line": latest_macd,
        "signal_line": latest_signal,
        "histogram": latest_hist,
        "signal": _macd_signal(latest_macd, latest_signal),
    }

    # SMA (20 and 50)
    sma_20 = sma(closes, 20)
    sma_50 = sma(closes, 50)
    latest_sma20 = next((v for v in reversed(sma_20) if v is not None), None)
    latest_sma50 = next((v for v in reversed(sma_50) if v is not None), None)
    latest_price = closes[-1] if closes else None
    result["sma"] = {
        "sma_20": latest_sma20,
        "sma_50": latest_sma50,
        "signal": _sma_signal(latest_price, latest_sma20, latest_sma50),
    }

    # EMA (12 and 26)
    ema_12 = ema(closes, 12)
    ema_26 = ema(closes, 26)
    latest_ema12 = next((v for v in reversed(ema_12) if v is not None), None)
    latest_ema26 = next((v for v in reversed(ema_26) if v is not None), None)
    result["ema"] = {
        "ema_12": latest_ema12,
        "ema_26": latest_ema26,
        "signal": _ema_signal(latest_ema12, latest_ema26),
    }

    # Bollinger Bands
    bb = bollinger_bands(closes)
    latest_upper = next((v for v in reversed(bb["upper"]) if v is not None), None)
    latest_lower = next((v for v in reversed(bb["lower"]) if v is not None), None)
    latest_mid = next((v for v in reversed(bb["middle"]) if v is not None), None)
    latest_bw = next((v for v in reversed(bb["bandwidth"]) if v is not None), None)
    result["bollinger_bands"] = {
        "upper": latest_upper,
        "middle": latest_mid,
        "lower": latest_lower,
        "bandwidth": latest_bw,
        "signal": _bb_signal(latest_price, latest_upper, latest_lower),
    }

    # Overall summary
    signals = [
        result["rsi"]["signal"],
        result["macd"]["signal"],
        result["sma"]["signal"],
        result["ema"]["signal"],
        result["bollinger_bands"]["signal"],
    ]
    bullish = sum(1 for s in signals if s == "bullish")
    bearish = sum(1 for s in signals if s == "bearish")

    if bullish > bearish:
        result["overall_signal"] = "bullish"
    elif bearish > bullish:
        result["overall_signal"] = "bearish"
    else:
        result["overall_signal"] = "neutral"

    result["signal_counts"] = {"bullish": bullish, "bearish": bearish, "neutral": len(signals) - bullish - bearish}

    return result


def _rsi_signal(rsi_val: float | None) -> str:
    if rsi_val is None:
        return "neutral"
    if rsi_val < 30:
        return "bullish"  # oversold
    if rsi_val > 70:
        return "bearish"  # overbought
    return "neutral"


def _macd_signal(macd_val: float | None, signal_val: float | None) -> str:
    if macd_val is None or signal_val is None:
        return "neutral"
    if macd_val > signal_val:
        return "bullish"
    if macd_val < signal_val:
        return "bearish"
    return "neutral"


def _sma_signal(price: float | None, sma20: float | None, sma50: float | None) -> str:
    if price is None or sma20 is None:
        return "neutral"
    if sma50 is not None:
        if sma20 > sma50 and price > sma20:
            return "bullish"
        if sma20 < sma50 and price < sma20:
            return "bearish"
    elif price > sma20:
        return "bullish"
    elif price < sma20:
        return "bearish"
    return "neutral"


def _ema_signal(ema12: float | None, ema26: float | None) -> str:
    if ema12 is None or ema26 is None:
        return "neutral"
    if ema12 > ema26:
        return "bullish"
    if ema12 < ema26:
        return "bearish"
    return "neutral"


def _bb_signal(price: float | None, upper: float | None, lower: float | None) -> str:
    if price is None or upper is None or lower is None:
        return "neutral"
    if price <= lower:
        return "bullish"  # at lower band = potential bounce
    if price >= upper:
        return "bearish"  # at upper band = potential pullback
    return "neutral"
