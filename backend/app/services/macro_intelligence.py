"""Macro intelligence service for economic indicators.

Fetches macro data from yfinance proxy tickers:
- ^VIX: CBOE Volatility Index (fear gauge)
- DX-Y.NYB: US Dollar Index (DXY)
- ^TNX: 10-Year Treasury Yield
- ^IRX: 13-Week Treasury Bill Rate
- GC=F: Gold futures (inflation hedge proxy)
- CL=F: Crude Oil WTI futures

Uses yf.download() for batch fetching (1 HTTP request for all tickers)
to avoid rate limiting.
"""

import asyncio
import logging
import time

import yfinance as yf

from app.services.cache import get_or_fetch, MACRO_TTL

logger = logging.getLogger(__name__)

# Macro tickers and their human-readable names
MACRO_TICKERS = {
    "^VIX": {"name": "VIX (Volatility Index)", "category": "volatility"},
    "DX-Y.NYB": {"name": "US Dollar Index (DXY)", "category": "currency"},
    "^TNX": {"name": "10-Year Treasury Yield", "category": "rates"},
    "^IRX": {"name": "13-Week T-Bill Rate", "category": "rates"},
    "GC=F": {"name": "Gold Futures", "category": "commodities"},
    "SI=F": {"name": "Silver Futures", "category": "commodities"},
    "CL=F": {"name": "Crude Oil WTI", "category": "commodities"},
    "NG=F": {"name": "Natural Gas", "category": "commodities"},
    "HG=F": {"name": "Copper Futures", "category": "commodities"},
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
    elif "Silver" in name:
        if change_pct > 1.5:
            return "Silver rallying — industrial + safe-haven demand increasing"
        elif change_pct < -1.5:
            return "Silver declining — reduced industrial demand or risk-on shift"
        return f"Silver {direction} — tracking precious metals complex"
    elif "Oil" in name or "Crude" in name:
        if change_pct > 2.0:
            return "Oil surging — inflation risk, energy cost pressure"
        elif change_pct < -2.0:
            return "Oil dropping — deflationary signal, demand concerns"
        return f"Oil {direction} — neutral energy market"
    elif "Natural Gas" in name:
        if change_pct > 3.0:
            return "Natural gas spiking — supply concerns, utility cost pressure"
        elif change_pct < -3.0:
            return "Natural gas plunging — oversupply or mild weather outlook"
        return f"Natural gas {direction} — normal seasonal movement"
    elif "Copper" in name:
        if change_pct > 1.0:
            return "Copper rising — signal of industrial expansion and economic growth"
        elif change_pct < -1.0:
            return "Copper falling — potential economic slowdown signal (Dr. Copper)"
        return f"Copper {direction} — neutral industrial demand"
    return f"{name} {direction}"


def _sync_batch_fetch_macro() -> dict[str, dict]:
    """Batch-fetch all macro tickers with a single yf.download() call.

    Returns dict mapping ticker -> {"price": float, "prev_close": float}
    """
    symbols = list(MACRO_TICKERS.keys())
    results: dict[str, dict] = {}

    for attempt in range(3):
        try:
            # yf.download fetches all tickers in one batch HTTP request
            df = yf.download(
                symbols,
                period="5d",
                interval="1d",
                group_by="ticker",
                progress=False,
                threads=False,
            )

            if df.empty:
                logger.warning("yf.download returned empty dataframe (attempt %d)", attempt + 1)
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                return results

            for sym in symbols:
                try:
                    if len(symbols) == 1:
                        ticker_df = df
                    else:
                        ticker_df = df[sym]

                    # Drop NaN rows
                    ticker_df = ticker_df.dropna(subset=["Close"])
                    if len(ticker_df) < 1:
                        continue

                    price = float(ticker_df["Close"].iloc[-1])
                    prev_close = float(ticker_df["Close"].iloc[-2]) if len(ticker_df) >= 2 else price

                    if price > 0:
                        results[sym] = {
                            "price": price,
                            "prev_close": prev_close,
                        }
                except Exception as e:
                    logger.debug("Failed to extract data for %s: %s", sym, e)

            if results:
                return results

        except Exception as e:
            logger.warning("yf.download macro batch failed (attempt %d): %s", attempt + 1, e)
            if attempt < 2:
                time.sleep(2 * (attempt + 1))

    return results


def _build_indicator(ticker_symbol: str, raw: dict) -> dict | None:
    """Build indicator dict from raw price data."""
    meta = MACRO_TICKERS.get(ticker_symbol)
    if not meta or not raw:
        return None

    price = raw["price"]
    prev_close = raw["prev_close"]
    change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0

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
        "ticker": ticker_symbol,
        "value": round(price, 4),
        "change_percent": round(change_pct, 2),
        "previous_close": round(prev_close, 4),
        "trend": _get_trend(change_pct),
        "impact_description": impact,
        "category": category,
    }


async def get_macro_indicator(ticker_symbol: str) -> dict | None:
    """Fetch a single macro indicator via the batch cache."""
    all_indicators = await get_all_macro_indicators()
    for ind in all_indicators:
        meta = MACRO_TICKERS.get(ticker_symbol)
        if meta and ind["name"] == meta["name"]:
            return ind
    return None


async def get_all_macro_indicators() -> list[dict]:
    """Fetch all macro indicators with a single batch download (cached)."""

    async def _fetch():
        try:
            raw_data = await asyncio.to_thread(_sync_batch_fetch_macro)
            indicators = []
            for sym in MACRO_TICKERS:
                raw = raw_data.get(sym)
                if raw:
                    ind = _build_indicator(sym, raw)
                    if ind:
                        indicators.append(ind)
            return indicators
        except Exception as e:
            logger.error("Macro batch fetch failed: %s", e)
            return []

    return await get_or_fetch("macro:all_indicators", _fetch, MACRO_TTL) or []


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
        elif "Silver" in ind["name"]:
            if abs(ind["change_percent"]) > 2:
                direction = "rallying" if ind["change_percent"] > 0 else "dropping"
                signals.append(f"Silver {direction}")
        elif "Oil" in ind["name"] or "Crude" in ind["name"]:
            if abs(ind["change_percent"]) > 2:
                direction = "surging" if ind["change_percent"] > 0 else "plunging"
                signals.append(f"Oil {direction} — watch inflation impact")
        elif "Copper" in ind["name"]:
            if abs(ind["change_percent"]) > 1.5:
                direction = "rising" if ind["change_percent"] > 0 else "falling"
                signals.append(f"Copper {direction} — industrial demand signal")
        elif "Natural Gas" in ind["name"]:
            if abs(ind["change_percent"]) > 3:
                direction = "spiking" if ind["change_percent"] > 0 else "plunging"
                signals.append(f"Natural gas {direction}")

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
