"""Quantitative scoring engine for investment predictions.

Pure NumPy computations: OHLCV arrays + macro data → 7 factor scores + composite.
Score first, explain second. The quant engine decides, the AI contextualizes.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return float(max(lo, min(hi, v)))


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b != 0 else default


def _ema(arr: np.ndarray, span: int) -> np.ndarray:
    """Exponential moving average (full length, initial NaN filled with SMA)."""
    alpha = 2.0 / (span + 1)
    out = np.empty_like(arr, dtype=np.float64)
    out[0] = arr[0]
    for i in range(1, len(arr)):
        out[i] = alpha * arr[i] + (1 - alpha) * out[i - 1]
    return out


def _sma(arr: np.ndarray, window: int) -> np.ndarray:
    """Simple moving average. First (window-1) entries are NaN."""
    out = np.full_like(arr, np.nan, dtype=np.float64)
    cs = np.cumsum(arr)
    out[window - 1:] = (cs[window - 1:] - np.concatenate([[0], cs[:-window]])) / window
    return out


def _true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """True Range starting from index 1 (length = len-1)."""
    prev_c = close[:-1]
    h = high[1:]
    l = low[1:]
    return np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))


def _wilder_smooth(arr: np.ndarray, period: int) -> np.ndarray:
    """Wilder smoothing (used for ADX)."""
    out = np.empty_like(arr, dtype=np.float64)
    out[:period] = np.nan
    out[period - 1] = np.nanmean(arr[:period])
    for i in range(period, len(arr)):
        out[i] = (out[i - 1] * (period - 1) + arr[i]) / period
    return out


# ---------------------------------------------------------------------------
# A. Trend Score
# ---------------------------------------------------------------------------

def _trend_score(close: np.ndarray, high: np.ndarray, low: np.ndarray) -> tuple[float, float]:
    """Returns (trend_score, adx_value)."""
    n = len(close)
    if n < 50:
        return 0.0, 0.0

    c = close[-1]

    # MA Alignment: 5 conditions
    ema12 = _ema(close, 12)
    ema26 = _ema(close, 26)
    sma20 = _sma(close, 20)
    sma50 = _sma(close, 50)

    conditions = [
        c > ema12[-1],
        c > ema26[-1],
        c > sma20[-1] if not np.isnan(sma20[-1]) else False,
        c > sma50[-1] if not np.isnan(sma50[-1]) else False,
        ema12[-1] > ema26[-1],
    ]
    ma_score = (sum(conditions) / 5) * 2 - 1  # map [0,1] → [-1,1]

    # MACD Composite
    macd_line = ema12 - ema26
    signal_line = _ema(macd_line, 9)
    histogram = macd_line - signal_line

    macd_sign = 1.0 if macd_line[-1] > 0 else -1.0
    crossover = 1.0 if macd_line[-1] > signal_line[-1] else -1.0
    hist_slope = 1.0 if len(histogram) >= 2 and histogram[-1] > histogram[-2] else -1.0
    macd_composite = (macd_sign + crossover + hist_slope) / 3.0

    # ADX (Wilder 14)
    period = 14
    if n < period + 2:
        return _clamp(0.35 * ma_score + 0.30 * macd_composite), 0.0

    tr = _true_range(high, low, close)
    plus_dm = np.maximum(high[1:] - high[:-1], 0.0)
    minus_dm = np.maximum(low[:-1] - low[1:], 0.0)

    # Zero out where the other is larger
    mask = plus_dm > minus_dm
    minus_dm[mask & (plus_dm > minus_dm)] = 0.0
    mask2 = minus_dm > plus_dm
    plus_dm[mask2] = 0.0
    # If equal, both zero
    eq_mask = plus_dm == minus_dm
    plus_dm[eq_mask] = 0.0
    minus_dm[eq_mask] = 0.0

    atr_smooth = _wilder_smooth(tr, period)
    plus_di_smooth = _wilder_smooth(plus_dm, period)
    minus_di_smooth = _wilder_smooth(minus_dm, period)

    plus_di = 100.0 * _safe_div(plus_di_smooth[-1], atr_smooth[-1])
    minus_di = 100.0 * _safe_div(minus_di_smooth[-1], atr_smooth[-1])

    di_sum = plus_di + minus_di
    dx_arr = np.abs(plus_di_smooth - minus_di_smooth) / np.maximum(plus_di_smooth + minus_di_smooth, 1e-10) * 100
    adx_arr = _wilder_smooth(dx_arr[period - 1:], period)
    adx_value = float(adx_arr[-1]) if len(adx_arr) > 0 and not np.isnan(adx_arr[-1]) else 0.0

    direction = 1.0 if plus_di > minus_di else -1.0
    strength = min(adx_value / 50.0, 1.0)
    adx_score = direction * strength

    trend = _clamp(0.35 * ma_score + 0.30 * macd_composite + 0.35 * adx_score)
    return trend, adx_value


# ---------------------------------------------------------------------------
# B. Mean-Reversion Score
# ---------------------------------------------------------------------------

def _mean_reversion_score(close: np.ndarray) -> float:
    n = len(close)
    if n < 20:
        return 0.0

    sma20 = _sma(close, 20)
    std20 = np.full_like(close, np.nan, dtype=np.float64)
    for i in range(19, n):
        std20[i] = np.std(close[i - 19 : i + 1], ddof=0)

    c = close[-1]
    s = sma20[-1]
    sd = std20[-1]

    if np.isnan(s) or np.isnan(sd) or sd < 1e-10:
        return 0.0

    # Bollinger %B reversion: 1 - 2*%B (so below band = bullish)
    upper = s + 2 * sd
    lower = s - 2 * sd
    pct_b = _safe_div(c - lower, upper - lower, 0.5)
    bb_rev = _clamp(1.0 - 2.0 * pct_b)

    # RSI reversion
    rsi = _compute_rsi(close, 14)
    rsi_rev = _clamp((50.0 - rsi) / 50.0)

    # Z-score
    z = _safe_div(-(c - s), sd)
    z_norm = _clamp(z / 3.0)

    return _clamp(0.35 * bb_rev + 0.35 * rsi_rev + 0.30 * z_norm)


def _compute_rsi(close: np.ndarray, period: int = 14) -> float:
    if len(close) < period + 1:
        return 50.0
    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss < 1e-10:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


# ---------------------------------------------------------------------------
# C. Momentum Score
# ---------------------------------------------------------------------------

def _momentum_score(close: np.ndarray, high: np.ndarray, low: np.ndarray) -> float:
    n = len(close)
    if n < 22:
        return 0.0

    c = close[-1]

    # ROC at 5/10/21 days, normalized with tanh(ROC/k)
    def roc_norm(period: int, k: float) -> float:
        if n <= period:
            return 0.0
        roc = (c - close[-1 - period]) / close[-1 - period] * 100.0
        return math.tanh(roc / k)

    roc5 = roc_norm(5, 5.0)
    roc10 = roc_norm(10, 8.0)
    roc21 = roc_norm(21, 15.0)

    # RSI Momentum
    rsi = _compute_rsi(close, 14)
    rsi_mom = _clamp((rsi - 50.0) / 50.0)

    # Histogram Momentum: tanh(hist / (ATR * 0.1))
    ema12 = _ema(close, 12)
    ema26 = _ema(close, 26)
    macd_line = ema12 - ema26
    signal_line = _ema(macd_line, 9)
    hist = macd_line[-1] - signal_line[-1]

    tr = _true_range(high, low, close)
    atr = float(np.mean(tr[-14:])) if len(tr) >= 14 else float(np.mean(tr)) if len(tr) > 0 else 1.0
    hist_mom = math.tanh(_safe_div(hist, atr * 0.1))

    return _clamp(
        0.20 * roc5 + 0.25 * roc10 + 0.25 * roc21 + 0.15 * rsi_mom + 0.15 * hist_mom
    )


# ---------------------------------------------------------------------------
# D. Volume Score
# ---------------------------------------------------------------------------

def _volume_score(close: np.ndarray, volume: np.ndarray) -> float:
    n = len(close)
    if n < 21 or len(volume) < 21:
        return 0.0

    # OBV
    deltas = np.diff(close)
    obv = np.zeros(n, dtype=np.float64)
    for i in range(1, n):
        if deltas[i - 1] > 0:
            obv[i] = obv[i - 1] + volume[i]
        elif deltas[i - 1] < 0:
            obv[i] = obv[i - 1] - volume[i]
        else:
            obv[i] = obv[i - 1]

    obv_sma20 = _sma(obv, 20)
    obv_trend = 1.0 if obv[-1] > obv_sma20[-1] and not np.isnan(obv_sma20[-1]) else -1.0

    # Volume-price confirmation
    price_dir = 1.0 if close[-1] > close[-2] else -1.0
    vol_avg_5 = float(np.mean(volume[-5:]))
    vol_avg_20 = float(np.mean(volume[-20:]))
    vol_ratio = _safe_div(vol_avg_5, vol_avg_20, 1.0)
    vol_confirm = _clamp(price_dir * min(vol_ratio, 2.0) / 2.0)

    return _clamp(0.50 * obv_trend + 0.50 * vol_confirm)


# ---------------------------------------------------------------------------
# E. Support/Resistance Score
# ---------------------------------------------------------------------------

def _support_resistance_score(
    close: np.ndarray, high: np.ndarray, low: np.ndarray
) -> tuple[float, dict]:
    """Returns (score, {pivot, support_levels, resistance_levels})."""
    n = len(close)
    if n < 5:
        return 0.0, {}

    c = close[-1]

    # Classic Pivot Points from previous bar
    prev_h = float(high[-2])
    prev_l = float(low[-2])
    prev_c = float(close[-2])
    pivot = (prev_h + prev_l + prev_c) / 3.0
    s1 = 2 * pivot - prev_h
    r1 = 2 * pivot - prev_l
    s2 = pivot - (prev_h - prev_l)
    r2 = pivot + (prev_h - prev_l)

    # Williams Fractals (window=2)
    fractal_highs: list[float] = []
    fractal_lows: list[float] = []
    w = 2
    for i in range(w, n - w):
        if all(high[i] >= high[i - j] for j in range(1, w + 1)) and all(
            high[i] >= high[i + j] for j in range(1, w + 1)
        ):
            fractal_highs.append(float(high[i]))
        if all(low[i] <= low[i - j] for j in range(1, w + 1)) and all(
            low[i] <= low[i + j] for j in range(1, w + 1)
        ):
            fractal_lows.append(float(low[i]))

    # Cluster fractals within 2%
    def cluster(levels: list[float]) -> list[float]:
        if not levels:
            return []
        levels = sorted(levels)
        clusters: list[list[float]] = [[levels[0]]]
        for lv in levels[1:]:
            if abs(lv - clusters[-1][-1]) / max(clusters[-1][-1], 1e-10) < 0.02:
                clusters[-1].append(lv)
            else:
                clusters.append([lv])
        return [sum(cl) / len(cl) for cl in clusters]

    res_levels = sorted(set(cluster(fractal_highs) + [r1, r2]))
    sup_levels = sorted(set(cluster(fractal_lows) + [s1, s2]))

    # Nearest support/resistance
    supports_below = [s for s in sup_levels if s < c]
    resistances_above = [r for r in res_levels if r > c]
    nearest_sup = max(supports_below) if supports_below else s1
    nearest_res = min(resistances_above) if resistances_above else r1

    dist_sup = abs(c - nearest_sup)
    dist_res = abs(nearest_res - c)
    denom = dist_res + dist_sup
    if denom < 1e-10:
        prox = 0.0
    else:
        prox = (dist_res - dist_sup) / denom  # positive = closer to support (bearish), negative = closer to resistance (bullish)

    sr_info = {
        "pivot": round(pivot, 2),
        "s1": round(s1, 2),
        "s2": round(s2, 2),
        "r1": round(r1, 2),
        "r2": round(r2, 2),
        "nearest_support": round(nearest_sup, 2),
        "nearest_resistance": round(nearest_res, 2),
        "fractal_supports": [round(s, 2) for s in sup_levels[-5:]],
        "fractal_resistances": [round(r, 2) for r in res_levels[-5:]],
    }

    return _clamp(prox), sr_info


# ---------------------------------------------------------------------------
# F. Candlestick Patterns
# ---------------------------------------------------------------------------

def _candlestick_score(
    open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray
) -> tuple[float, list[str]]:
    """Detect patterns on latest bars. Returns (score, [pattern_names])."""
    n = len(close)
    if n < 5:
        return 0.0, []

    detected: list[tuple[str, float]] = []

    o, h, l, c = float(open_[-1]), float(high[-1]), float(low[-1]), float(close[-1])
    body = abs(c - o)
    full_range = h - l
    if full_range < 1e-10:
        return 0.0, []

    body_ratio = body / full_range
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    # Prior trend (5-bar)
    prior_trend = 1.0 if close[-1] > close[-6] else -1.0 if close[-1] < close[-6] else 0.0

    # Doji
    if body_ratio < 0.1:
        detected.append(("Doji", -prior_trend * 0.3))

    # Hammer (bullish) / Shooting Star (bearish)
    if body_ratio < 0.35:
        if lower_wick > 2 * body and upper_wick < body * 0.5:
            # Hammer-like
            if prior_trend < 0:
                detected.append(("Hammer", 0.6))
            else:
                detected.append(("Hanging Man", -0.4))
        elif upper_wick > 2 * body and lower_wick < body * 0.5:
            # Shooting star-like
            if prior_trend > 0:
                detected.append(("Shooting Star", -0.6))
            else:
                detected.append(("Inverted Hammer", 0.4))

    # Engulfing (2-bar)
    if n >= 2:
        po, pc = float(open_[-2]), float(close[-2])
        if pc < po and c > o and o <= pc and c >= po:
            detected.append(("Bullish Engulfing", 0.8))
        elif pc > po and c < o and o >= pc and c <= po:
            detected.append(("Bearish Engulfing", -0.8))

    # Morning/Evening Star (3-bar)
    if n >= 3:
        o3, c3 = float(open_[-3]), float(close[-3])
        o2, c2 = float(open_[-2]), float(close[-2])
        body3 = abs(c3 - o3)
        body2 = abs(c2 - o2)
        body1 = body

        if body3 > 0 and body2 < body3 * 0.3 and body1 > body3 * 0.5:
            if c3 < o3 and c > o:
                detected.append(("Morning Star", 0.9))
            elif c3 > o3 and c < o:
                detected.append(("Evening Star", -0.9))

    if not detected:
        return 0.0, []

    # Take the pattern with the largest absolute score
    best = max(detected, key=lambda x: abs(x[1]))
    names = [d[0] for d in detected]
    return _clamp(best[1]), names


# ---------------------------------------------------------------------------
# G. Macro Score
# ---------------------------------------------------------------------------

def _macro_score(macro_indicators: list[dict]) -> float:
    """Full macro environment score using all available indicators.

    Components (weighted):
      - VIX fear gauge         (25%) — high VIX = bearish risk assets
      - Yield curve slope      (20%) — inverted = recession risk = bearish
      - DXY dollar strength    (15%) — strong dollar = bearish for stocks/crypto
      - Gold momentum          (15%) — rising gold = flight to safety = bearish risk
      - Oil momentum           (15%) — rising oil = inflation = mixed-to-bearish
      - Copper momentum        (10%) — "Dr. Copper" = economic health = bullish if rising
    """
    vix_val = None
    yield_10y = None
    yield_13w = None
    dxy_chg = None
    gold_chg = None
    oil_chg = None
    copper_chg = None

    for ind in macro_indicators:
        name = ind.get("name", "")
        chg = ind.get("change_percent", 0.0)
        if "VIX" in name:
            vix_val = ind["value"]
        elif "10-Year" in name:
            yield_10y = ind["value"]
        elif "13-Week" in name or "T-Bill" in name:
            yield_13w = ind["value"]
        elif "Dollar" in name or "DXY" in name:
            dxy_chg = chg
        elif "Gold" in name:
            gold_chg = chg
        elif "Crude Oil" in name or "WTI" in name:
            oil_chg = chg
        elif "Copper" in name:
            copper_chg = chg

    scored: list[tuple[float, float]] = []  # (score, weight)

    # VIX: high fear = bearish for risk assets
    if vix_val is not None:
        scored.append((-math.tanh((vix_val - 20) / 10), 0.25))

    # Yield curve: inverted = recession signal = bearish
    if yield_10y is not None and yield_13w is not None:
        scored.append((math.tanh((yield_10y - yield_13w) / 1.5), 0.20))

    # DXY: strong dollar hurts risk assets and commodities
    if dxy_chg is not None:
        scored.append((-math.tanh(dxy_chg / 1.0), 0.15))

    # Gold: rising gold = flight to safety = bearish for risk assets
    if gold_chg is not None:
        scored.append((-math.tanh(gold_chg / 2.0), 0.15))

    # Oil: rising oil = inflationary pressure = mildly bearish
    if oil_chg is not None:
        scored.append((-math.tanh(oil_chg / 3.0), 0.15))

    # Copper: rising copper = economic expansion = bullish
    if copper_chg is not None:
        scored.append((math.tanh(copper_chg / 2.0), 0.10))

    if not scored:
        return 0.0

    total_weight = sum(w for _, w in scored)
    if total_weight < 1e-10:
        return 0.0

    weighted_sum = sum(s * w for s, w in scored) / total_weight
    return _clamp(weighted_sum)


# ---------------------------------------------------------------------------
# H. Sentiment Score
# ---------------------------------------------------------------------------

def _sentiment_score(enhanced_sentiment: dict | None) -> float:
    """Convert the enhanced sentiment unified_score into a factor.

    The enhanced_sentiment service already computes a weighted average of
    AI sentiment, news tone, social buzz, and market mood into a single
    unified_score in [-1, +1]. We use it directly, applying tanh scaling
    so extreme values (> ±0.5) don't dominate.
    """
    if not enhanced_sentiment:
        return 0.0

    raw = enhanced_sentiment.get("unified_score", 0.0)
    if raw is None:
        return 0.0

    # Scale: unified_score is already [-1, 1] but tends to cluster near 0.
    # Amplify with tanh(score * 2) so a 0.3 score becomes ~0.54 factor.
    return _clamp(math.tanh(raw * 2.0))


# ---------------------------------------------------------------------------
# Risk Metrics
# ---------------------------------------------------------------------------

def _risk_metrics(
    close: np.ndarray, macro_indicators: list[dict]
) -> tuple[dict, float]:
    """Compute Sharpe, MaxDD, HV. Returns (metrics_dict, vol_score)."""
    n = len(close)
    if n < 21:
        return {"sharpe_ratio": 0.0, "max_drawdown": 0.0, "historical_volatility": 0.0}, 0.0

    # Historical Volatility (20-day annualized)
    log_returns = np.log(close[1:] / close[:-1])
    hv_20 = float(np.std(log_returns[-20:], ddof=1)) * math.sqrt(252) * 100

    # Risk-free rate from 13W T-bill
    rf_annual = 0.0
    for ind in macro_indicators:
        name = ind.get("name", "")
        if "13-Week" in name or "T-Bill" in name:
            rf_annual = ind["value"] / 100.0  # e.g. 5.2 → 0.052
            break
    rf_daily = rf_annual / 252.0

    # Sharpe Ratio (63-day window)
    window = min(63, len(log_returns))
    recent_returns = log_returns[-window:]
    excess = recent_returns - rf_daily
    sharpe = 0.0
    if len(excess) > 1:
        std = float(np.std(excess, ddof=1))
        if std > 1e-10:
            sharpe = float(np.mean(excess)) / std * math.sqrt(252)

    # Max Drawdown (63-day)
    prices_63 = close[-min(63, n):]
    cummax = np.maximum.accumulate(prices_63)
    drawdowns = (prices_63 - cummax) / cummax
    max_dd = float(np.min(drawdowns)) * 100  # negative percentage

    metrics = {
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": round(max_dd, 2),
        "historical_volatility": round(hv_20, 2),
    }

    # Vol score: adjusts confidence (not direction)
    vol_score = _clamp(-math.tanh((hv_20 - 25) / 15))

    return metrics, vol_score


# ---------------------------------------------------------------------------
# Composite Scoring
# ---------------------------------------------------------------------------

WEIGHTS_TRENDING = {
    "trend": 0.25,
    "mean_reversion": 0.05,
    "momentum": 0.20,
    "volume": 0.08,
    "support_resistance": 0.05,
    "candlestick": 0.05,
    "macro": 0.17,
    "sentiment": 0.15,
}

WEIGHTS_RANGE = {
    "trend": 0.08,
    "mean_reversion": 0.25,
    "momentum": 0.12,
    "volume": 0.08,
    "support_resistance": 0.12,
    "candlestick": 0.05,
    "macro": 0.13,
    "sentiment": 0.17,
}


def _determine_verdict(composite: float) -> tuple[str, float]:
    """Map composite score to verdict + base confidence."""
    if composite >= 0.50:
        return "strong_buy", 0.80
    elif composite >= 0.25:
        return "buy", 0.65
    elif composite >= -0.25:
        return "neutral", 0.45
    elif composite >= -0.50:
        return "sell", 0.65
    else:
        return "strong_sell", 0.80


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def _factor_agreement(factors: dict[str, float]) -> float:
    """Measure directional agreement across factors.

    Returns a multiplier in [0.7, 1.3]:
      - 1.3 if all factors agree in direction (high conviction)
      - 1.0 if mixed
      - 0.7 if factors are strongly split (low conviction)
    """
    non_zero = [v for v in factors.values() if abs(v) > 0.05]
    if len(non_zero) < 2:
        return 1.0

    bullish = sum(1 for v in non_zero if v > 0)
    bearish = sum(1 for v in non_zero if v < 0)
    total = len(non_zero)

    # agreement_ratio: 1.0 = unanimous, 0.5 = perfectly split
    agreement_ratio = max(bullish, bearish) / total

    # Map [0.5, 1.0] → [0.7, 1.3]
    return 0.7 + (agreement_ratio - 0.5) * 1.2


def compute_quant_scores(
    history: list[dict],
    macro_indicators: list[dict],
    enhanced_sentiment: dict | None = None,
) -> dict[str, Any]:
    """Compute full quantitative scoring from OHLCV history + macro + sentiment.

    Parameters
    ----------
    history : list[dict]
        List of {date, open, high, low, close, volume} dicts, chronological.
    macro_indicators : list[dict]
        List of macro indicator dicts with {name, value, ...}.
    enhanced_sentiment : dict | None
        Enhanced sentiment dict with unified_score in [-1, 1].

    Returns
    -------
    dict with: factors, composite_score, verdict, confidence, regime,
               risk_metrics, support_resistance, candlestick_patterns, weights,
               factor_agreement.
    """
    if not history or len(history) < 30:
        return _empty_result()

    # Extract arrays
    close = np.array([r["close"] for r in history], dtype=np.float64)
    high = np.array([r["high"] for r in history], dtype=np.float64)
    low = np.array([r["low"] for r in history], dtype=np.float64)
    open_ = np.array([r["open"] for r in history], dtype=np.float64)
    volume = np.array([r["volume"] for r in history], dtype=np.float64)

    # Compute 8 factors
    trend, adx_value = _trend_score(close, high, low)
    mean_rev = _mean_reversion_score(close)
    momentum = _momentum_score(close, high, low)
    vol_score = _volume_score(close, volume)
    sr_score, sr_info = _support_resistance_score(close, high, low)
    candle_score, candle_patterns = _candlestick_score(open_, high, low, close)
    macro = _macro_score(macro_indicators)
    sentiment = _sentiment_score(enhanced_sentiment)

    # Regime detection
    regime = "trending" if adx_value > 25 else "range_bound"
    weights = WEIGHTS_TRENDING if regime == "trending" else WEIGHTS_RANGE

    factors = {
        "trend": round(trend, 4),
        "mean_reversion": round(mean_rev, 4),
        "momentum": round(momentum, 4),
        "volume": round(vol_score, 4),
        "support_resistance": round(sr_score, 4),
        "candlestick": round(candle_score, 4),
        "macro": round(macro, 4),
        "sentiment": round(sentiment, 4),
    }

    # Weighted composite
    composite = sum(factors[k] * weights[k] for k in factors)
    composite = _clamp(composite)

    # Verdict + confidence
    verdict, base_conf = _determine_verdict(composite)

    # Risk metrics → adjust confidence
    risk, risk_vol_score = _risk_metrics(close, macro_indicators)

    # Factor agreement → adjust confidence
    agreement = _factor_agreement(factors)

    confidence = base_conf * (0.6 + 0.4 * (1 + risk_vol_score) / 2) * agreement
    confidence = max(0.0, min(1.0, confidence))

    return {
        "factors": factors,
        "composite_score": round(composite, 4),
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "regime": regime,
        "adx": round(adx_value, 2),
        "weights": {k: round(v, 2) for k, v in weights.items()},
        "risk_metrics": risk,
        "support_resistance": sr_info,
        "candlestick_patterns": candle_patterns,
        "risk_vol_score": round(risk_vol_score, 4),
        "factor_agreement": round(agreement, 4),
    }


def _empty_result() -> dict[str, Any]:
    """Return empty/neutral result when insufficient data."""
    return {
        "factors": {
            "trend": 0.0,
            "mean_reversion": 0.0,
            "momentum": 0.0,
            "volume": 0.0,
            "support_resistance": 0.0,
            "candlestick": 0.0,
            "macro": 0.0,
            "sentiment": 0.0,
        },
        "composite_score": 0.0,
        "verdict": "neutral",
        "confidence": 0.0,
        "regime": "unknown",
        "adx": 0.0,
        "weights": {},
        "risk_metrics": {
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "historical_volatility": 0.0,
        },
        "support_resistance": {},
        "candlestick_patterns": [],
        "risk_vol_score": 0.0,
        "factor_agreement": 1.0,
    }
