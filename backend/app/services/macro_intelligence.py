"""Macro intelligence service for economic indicators.

Fetches macro data from yfinance proxy tickers:
- ^VIX: CBOE Volatility Index (fear gauge)
- DX-Y.NYB: US Dollar Index (DXY)
- ^TNX: 10-Year Treasury Yield
- ^IRX: 13-Week Treasury Bill Rate
- GC=F: Gold futures (inflation hedge proxy)
- CL=F: Crude Oil WTI futures
"""

import logging
from datetime import datetime, timezone

import yfinance as yf

logger = logging.getLogger(__name__)

# Macro tickers and their human-readable names
MACRO_TICKERS = {
    "^VIX": {"name": "VIX (Volatility Index)", "category": "volatility"},
    "DX-Y.NYB": {"name": "US Dollar Index (DXY)", "category": "currency"},
    "^TNX": {"name": "10-Year Treasury Yield", "category": "rates"},
    "^IRX": {"name": "13-Week T-Bill Rate", "category": "rates"},
    "GC=F": {"name": "Gold Futures", "category": "commodities"},
    "CL=F": {"name": "Crude Oil WTI", "category": "commodities"},
}


def _get_trend(change_pct: float) -> str:
    """Classify change as up/down/stable."""
    if change_pct > 0.3:
        return "up"
    elif change_pct < -0.3:
        return "down"
    return "stable"


def _vix_impact(value: float) -> str:
    if value >= 30:
        return "Extreme fear — markets highly volatile, risk-off environment"
    elif value >= 20:
        return "Elevated volatility — uncertainty rising, consider defensive positioning"
    elif value >= 15:
        return "Normal volatility — balanced risk environment"
    return "Low volatility — complacency, markets calm"


def _dxy_impact(change_pct: float) -> str:
    if change_pct > 0.5:
        return "Dollar strengthening — headwind for commodities and EM assets"
    elif change_pct < -0.5:
        return "Dollar weakening — tailwind for commodities and international equities"
    return "Dollar stable — neutral macro signal"


def _yield_impact(value: float, change_pct: float) -> str:
    parts = []
    if value >= 5.0:
        parts.append(f"Yields elevated at {value:.2f}%")
    elif value >= 4.0:
        parts.append(f"Yields moderately high at {value:.2f}%")
    else:
        parts.append(f"Yields at {value:.2f}%")

    if change_pct > 0.5:
        parts.append("rising — pressure on growth stocks and bonds")
    elif change_pct < -0.5:
        parts.append("falling — supportive for equities and bonds")
    else:
        parts.append("stable — neutral rate environment")
    return ", ".join(parts)


def _commodity_impact(name: str, change_pct: float) -> str:
    direction = "rising" if change_pct > 0.5 else "falling" if change_pct < -0.5 else "stable"
    if "Gold" in name:
        if change_pct > 1.0:
            return "Gold rallying — safe-haven demand, potential inflation concerns"
        elif change_pct < -1.0:
            return "Gold declining — risk-on sentiment, reduced inflation fears"
        return "Gold stable — balanced macro outlook"
    elif "Oil" in name or "Crude" in name:
        if change_pct > 2.0:
            return "Oil surging — inflation risk, energy cost pressure"
        elif change_pct < -2.0:
            return "Oil dropping — deflationary signal, demand concerns"
        return f"Oil {direction} — neutral energy market"
    return f"{name} {direction}"


def get_macro_indicator(ticker_symbol: str) -> dict | None:
    """Fetch a single macro indicator from yfinance."""
    meta = MACRO_TICKERS.get(ticker_symbol)
    if not meta:
        return None

    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.fast_info
        price = info.get("lastPrice", 0.0) or info.get("regularMarketPrice", 0.0)
        prev_close = info.get("previousClose", 0.0) or info.get("regularMarketPreviousClose", 0.0)

        if not price:
            return None

        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0

        # Generate impact description based on category
        category = meta["category"]
        name = meta["name"]
        if "VIX" in ticker_symbol:
            impact = _vix_impact(price)
        elif "DX-Y" in ticker_symbol:
            impact = _dxy_impact(change_pct)
        elif category == "rates":
            impact = _yield_impact(price, change_pct)
        else:
            impact = _commodity_impact(name, change_pct)

        return {
            "name": name,
            "value": round(price, 4),
            "change_percent": round(change_pct, 2),
            "previous_close": round(prev_close, 4),
            "trend": _get_trend(change_pct),
            "impact_description": impact,
            "category": category,
        }
    except Exception as e:
        logger.warning("Failed to fetch macro indicator %s: %s", ticker_symbol, e)
        return None


def get_all_macro_indicators() -> list[dict]:
    """Fetch all macro indicators. Returns list of indicator dicts."""
    results = []
    for ticker_symbol in MACRO_TICKERS:
        indicator = get_macro_indicator(ticker_symbol)
        if indicator:
            results.append(indicator)
    return results


def get_macro_summary(indicators: list[dict]) -> dict:
    """Produce a high-level macro summary from indicator data.

    Returns dict with: environment, risk_level, key_signals
    """
    if not indicators:
        return {"environment": "unknown", "risk_level": "unknown", "key_signals": []}

    vix_val = None
    yield_val = None
    signals = []

    for ind in indicators:
        if "VIX" in ind["name"]:
            vix_val = ind["value"]
            if vix_val >= 25:
                signals.append("High volatility (VIX above 25)")
            elif vix_val <= 15:
                signals.append("Low volatility (VIX below 15)")
        elif "10-Year" in ind["name"]:
            yield_val = ind["value"]
            if ind["trend"] == "up":
                signals.append("Rising yields — tightening conditions")
            elif ind["trend"] == "down":
                signals.append("Falling yields — easing conditions")
        elif "Dollar" in ind["name"]:
            if ind["trend"] == "up":
                signals.append("Strengthening dollar")
            elif ind["trend"] == "down":
                signals.append("Weakening dollar")
        elif "Gold" in ind["name"]:
            if ind["trend"] == "up":
                signals.append("Gold rising — safe-haven demand")
        elif "Oil" in ind["name"] or "Crude" in ind["name"]:
            if abs(ind["change_percent"]) > 2:
                direction = "surging" if ind["change_percent"] > 0 else "plunging"
                signals.append(f"Oil {direction} — watch inflation impact")

    # Determine risk level
    risk = "moderate"
    if vix_val is not None:
        if vix_val >= 30:
            risk = "high"
        elif vix_val >= 20:
            risk = "elevated"
        elif vix_val < 15:
            risk = "low"

    # Determine environment
    env = "neutral"
    if vix_val is not None and vix_val >= 25:
        env = "risk-off"
    elif vix_val is not None and vix_val < 15:
        env = "risk-on"

    return {
        "environment": env,
        "risk_level": risk,
        "key_signals": signals[:5],
    }
