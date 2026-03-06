"""Macro intelligence compatibility layer backed by normalized providers."""

from __future__ import annotations

from app.services.data_providers.macro import (
    MACRO_SERIES,
    _commodity_impact,
    _dxy_impact,
    _get_trend,
    _sync_batch_fetch_macro,
    _vix_impact,
    _yield_impact,
    macro_provider_chain,
)

MACRO_TICKERS = {
    series["ticker"]: {
        "name": series["name"],
        "category": series["category"],
    }
    for series in MACRO_SERIES.values()
}


async def get_macro_indicator(ticker_symbol: str) -> dict | None:
    ticker = str(ticker_symbol or "").strip()
    if not ticker:
        return None

    indicators = await get_all_macro_indicators()
    for indicator in indicators:
        if indicator.get("ticker") == ticker:
            return indicator
    return None


async def get_all_macro_indicators() -> list[dict]:
    return await macro_provider_chain.get_indicators()


def get_macro_summary(indicators: list[dict]) -> dict:
    if not indicators:
        return {"environment": "unknown", "risk_level": "unknown", "key_signals": []}

    vix_val = None
    signals: list[str] = []

    for indicator in indicators:
        name = indicator.get("name", "")
        change_percent = float(indicator.get("change_percent", 0.0) or 0.0)
        trend = indicator.get("trend", "stable")

        if "VIX" in name:
            vix_val = float(indicator.get("value", 0.0) or 0.0)
            if vix_val >= 25:
                signals.append("High volatility (VIX above 25)")
            elif vix_val <= 15:
                signals.append("Low volatility (VIX below 15)")
        elif "10-Year" in name:
            if trend == "up":
                signals.append("Rising yields — tightening conditions")
            elif trend == "down":
                signals.append("Falling yields — easing conditions")
        elif "Dollar" in name:
            if trend == "up":
                signals.append("Strengthening dollar")
            elif trend == "down":
                signals.append("Weakening dollar")
        elif "Gold" in name and trend == "up":
            signals.append("Gold rising — safe-haven demand")
        elif "Silver" in name and abs(change_percent) > 2:
            direction = "rallying" if change_percent > 0 else "dropping"
            signals.append(f"Silver {direction}")
        elif ("Oil" in name or "Crude" in name) and abs(change_percent) > 2:
            direction = "surging" if change_percent > 0 else "plunging"
            signals.append(f"Oil {direction} — watch inflation impact")
        elif "Copper" in name and abs(change_percent) > 1.5:
            direction = "rising" if change_percent > 0 else "falling"
            signals.append(f"Copper {direction} — industrial demand signal")
        elif "Natural Gas" in name and abs(change_percent) > 3:
            direction = "spiking" if change_percent > 0 else "plunging"
            signals.append(f"Natural gas {direction}")

    risk = "moderate"
    if vix_val is not None:
        if vix_val >= 30:
            risk = "high"
        elif vix_val >= 20:
            risk = "elevated"
        elif vix_val < 15:
            risk = "low"

    environment = "neutral"
    if vix_val is not None and vix_val >= 25:
        environment = "risk-off"
    elif vix_val is not None and vix_val < 15:
        environment = "risk-on"

    return {
        "environment": environment,
        "risk_level": risk,
        "key_signals": signals[:5],
    }
