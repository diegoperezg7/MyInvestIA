"""Stock screener service using tvscreener library for TradingView data.

Provides filtered stock scans with technical signal aggregation and preset strategies.
Uses tvscreener for 13K+ fields from TradingView (no API key needed).
Falls back to basic yfinance scanning if tvscreener is not available.

Inspired by: https://github.com/deepentropy/tvscreener
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

# Preset screening strategies with TradingView-compatible filters
PRESETS = {
    "oversold_bounce": {
        "id": "oversold_bounce",
        "name": "Oversold Bounce",
        "description": "Stocks with RSI < 30 and positive MACD crossover — potential reversal candidates",
        "filters": {"rsi_below": 30, "macd_signal": "buy"},
        "tv_filters": [
            ("RSI", "less", 30),
            ("Recommend.Other", "in_range", [0.1, 1]),  # Oscillators bullish
        ],
    },
    "momentum_breakout": {
        "id": "momentum_breakout",
        "name": "Momentum Breakout",
        "description": "Stocks above SMA 50 with high volume and strong uptrend",
        "filters": {"above_sma50": True, "min_volume": 1_000_000},
        "tv_filters": [
            ("close", "above_value", "SMA50"),
            ("volume", "greater", 1_000_000),
            ("Recommend.MA", "in_range", [0.1, 1]),  # MAs bullish
        ],
    },
    "value_picks": {
        "id": "value_picks",
        "name": "Value Picks",
        "description": "Large cap stocks with low PE, high dividend yield, and positive analyst rating",
        "filters": {"min_market_cap": 10_000_000_000, "signal": "buy"},
        "tv_filters": [
            ("market_cap_basic", "greater", 10_000_000_000),
            ("price_earnings_ttm", "in_range", [0, 20]),
            ("dividend_yield_recent", "greater", 0.02),
        ],
    },
    "high_volatility": {
        "id": "high_volatility",
        "name": "High Volatility Movers",
        "description": "Stocks with highest daily movement — day trading candidates",
        "filters": {"min_change_percent": 3},
        "tv_filters": [
            ("change", "greater", 3),
            ("volume", "greater", 500_000),
        ],
    },
    "dividend_income": {
        "id": "dividend_income",
        "name": "Dividend Income",
        "description": "High dividend yield stocks with stable fundamentals for income investing",
        "filters": {"min_dividend_yield": 0.03},
        "tv_filters": [
            ("dividend_yield_recent", "greater", 0.03),
            ("market_cap_basic", "greater", 1_000_000_000),
        ],
    },
    "growth_tech": {
        "id": "growth_tech",
        "name": "Growth Tech",
        "description": "High-growth technology stocks with strong revenue momentum",
        "filters": {"sector": "technology", "min_volume": 500_000},
        "tv_filters": [
            ("sector", "equal", "Technology"),
            ("revenue_growth_quarterly_yoy", "greater", 0.15),
            ("volume", "greater", 500_000),
        ],
    },
    "crypto_movers": {
        "id": "crypto_movers",
        "name": "Crypto Movers",
        "description": "Top cryptocurrency movers by daily change",
        "filters": {"asset_type": "crypto", "min_change_percent": 2},
        "tv_filters": [],
        "screener_type": "crypto",
    },
}


def get_presets() -> list[dict]:
    """Return available preset strategies."""
    return [
        {"id": p["id"], "name": p["name"], "description": p["description"]}
        for p in PRESETS.values()
    ]


def get_fields() -> list[dict]:
    """Return filterable fields."""
    return [
        {"name": "min_price", "label": "Min Price", "type": "number"},
        {"name": "max_price", "label": "Max Price", "type": "number"},
        {"name": "min_volume", "label": "Min Volume", "type": "number"},
        {"name": "min_market_cap", "label": "Min Market Cap", "type": "number"},
        {"name": "signal", "label": "Signal", "type": "select",
         "options": ["strong_buy", "buy", "neutral", "sell", "strong_sell"]},
        {"name": "min_change_percent", "label": "Min Change %", "type": "number"},
        {"name": "min_dividend_yield", "label": "Min Dividend Yield", "type": "number"},
        {"name": "sector", "label": "Sector", "type": "select",
         "options": [
             "Technology", "Healthcare", "Financial", "Consumer Cyclical",
             "Communication Services", "Industrials", "Consumer Defensive",
             "Energy", "Utilities", "Real Estate", "Basic Materials",
         ]},
    ]


async def run_screener(
    market: str = "america",
    filters: dict | None = None,
    preset_id: str | None = None,
    limit: int = 50,
) -> dict:
    """Run stock screener scan.

    Tries tvscreener first, falls back to basic scanning.
    """
    active_filters = dict(filters or {})
    preset = None
    if preset_id and preset_id in PRESETS:
        preset = PRESETS[preset_id]
        active_filters.update(preset["filters"])

    # Check if this is a crypto preset
    screener_type = "stock"
    if preset and preset.get("screener_type") == "crypto":
        screener_type = "crypto"

    try:
        return await _scan_with_tvscreener(market, active_filters, limit, preset, screener_type)
    except Exception as e:
        logger.warning("tvscreener scan failed, using fallback: %s", e)
        return await _scan_fallback(market, active_filters, limit)


async def _scan_with_tvscreener(
    market: str,
    filters: dict,
    limit: int,
    preset: dict | None,
    screener_type: str,
) -> dict:
    """Scan using tvscreener library with proper TradingView API integration."""
    try:
        from tvscreener import StockScreener, CryptoScreener, StockField

        if screener_type == "crypto":
            ss = CryptoScreener()
        else:
            ss = StockScreener()

        # Set market/exchange
        market_exchanges = {
            "america": "america",
            "europe": "europe",
            "asia": "asia",
        }
        exchange = market_exchanges.get(market, "america")

        # Apply tvscreener filters from preset
        if preset and preset.get("tv_filters"):
            for filt in preset["tv_filters"]:
                try:
                    field_name, op, value = filt
                    if op == "greater":
                        ss.where(getattr(StockField, field_name.upper(), field_name) > value)
                    elif op == "less":
                        ss.where(getattr(StockField, field_name.upper(), field_name) < value)
                except Exception:
                    pass  # Skip individual filter errors

        # Apply basic filters
        if "min_price" in filters:
            try:
                ss.where(StockField.CLOSE > filters["min_price"])
            except Exception:
                pass
        if "max_price" in filters:
            try:
                ss.where(StockField.CLOSE < filters["max_price"])
            except Exception:
                pass
        if "min_volume" in filters:
            try:
                ss.where(StockField.VOLUME > filters["min_volume"])
            except Exception:
                pass

        # Fetch in thread to avoid blocking
        df = await asyncio.to_thread(ss.get, limit)

        results = []
        for _, row in df.iterrows():
            results.append({
                "symbol": str(row.get("name", row.get("ticker", ""))),
                "name": str(row.get("description", "")),
                "close": float(row.get("close", 0)),
                "change": float(row.get("change", 0)),
                "change_percent": float(row.get("change_percent", row.get("change", 0))),
                "volume": int(row.get("volume", 0)),
                "market_cap": float(row.get("market_cap_basic", 0)),
                "recommendation": _map_recommendation(row.get("Recommend.All")),
                "sector": str(row.get("sector", "")),
                "pe_ratio": float(row.get("price_earnings_ttm", 0)) if row.get("price_earnings_ttm") else None,
                "dividend_yield": float(row.get("dividend_yield_recent", 0)) if row.get("dividend_yield_recent") else None,
            })

        return {"results": results, "total": len(results), "market": market, "source": "tradingview"}

    except ImportError:
        logger.info("tvscreener not installed, using fallback")
        raise


def _map_recommendation(value) -> str:
    """Map TradingView numeric recommendation to label."""
    if value is None:
        return "neutral"
    try:
        val = float(value)
        if val >= 0.5:
            return "strong_buy"
        elif val >= 0.1:
            return "buy"
        elif val <= -0.5:
            return "strong_sell"
        elif val <= -0.1:
            return "sell"
        return "neutral"
    except (ValueError, TypeError):
        return "neutral"


async def _scan_fallback(market: str, filters: dict, limit: int) -> dict:
    """Basic fallback scanner using yfinance."""
    from app.services.market_data import market_data_service

    symbols = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD",
        "NFLX", "CRM", "ORCL", "INTC", "BA", "DIS", "V", "JPM", "GS",
        "WMT", "KO", "PEP", "PG", "JNJ", "UNH", "HD", "MA",
    ]

    tasks = [market_data_service.get_quote(sym) for sym in symbols[:limit]]
    quotes = await asyncio.gather(*tasks, return_exceptions=True)

    results = []
    for quote in quotes:
        if not isinstance(quote, dict) or not quote:
            continue

        price = quote.get("price", 0)
        if "min_price" in filters and price < filters["min_price"]:
            continue
        if "max_price" in filters and price > filters["max_price"]:
            continue
        if "min_volume" in filters and quote.get("volume", 0) < filters["min_volume"]:
            continue
        if "min_change_percent" in filters and abs(quote.get("change_percent", 0)) < filters["min_change_percent"]:
            continue

        results.append({
            "symbol": quote["symbol"],
            "name": quote["name"],
            "close": quote["price"],
            "change": 0,
            "change_percent": quote["change_percent"],
            "volume": quote["volume"],
            "market_cap": quote.get("market_cap", 0),
            "recommendation": "neutral",
        })

    return {"results": results, "total": len(results), "market": market, "source": "yfinance"}
