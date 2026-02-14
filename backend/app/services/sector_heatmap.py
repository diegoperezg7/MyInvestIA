"""Sector heatmap and market breadth service."""

import logging
from datetime import datetime

import yfinance as yf

from app.services import cache

logger = logging.getLogger(__name__)

HEATMAP_TTL = 900     # 15 min
BREADTH_TTL = 900     # 15 min

# 11 GICS sector ETFs
SECTOR_ETFS = [
    {"symbol": "XLK", "name": "Technology"},
    {"symbol": "XLF", "name": "Financials"},
    {"symbol": "XLV", "name": "Health Care"},
    {"symbol": "XLE", "name": "Energy"},
    {"symbol": "XLY", "name": "Consumer Discretionary"},
    {"symbol": "XLP", "name": "Consumer Staples"},
    {"symbol": "XLI", "name": "Industrials"},
    {"symbol": "XLB", "name": "Materials"},
    {"symbol": "XLRE", "name": "Real Estate"},
    {"symbol": "XLU", "name": "Utilities"},
    {"symbol": "XLC", "name": "Communication Services"},
]

# Representative S&P 500 stocks for breadth calculation
BREADTH_STOCKS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "JPM", "V",
    "UNH", "JNJ", "MA", "HD", "PG", "COST", "XOM", "MRK", "ABBV", "CRM",
    "ADBE", "PEP", "KO", "CVX", "LLY", "WMT", "MCD", "CSCO", "NFLX", "AMD",
    "BAC", "TMO", "INTC", "DIS", "PFE", "CMCSA", "ABT", "NKE", "TXN", "COP",
    "GS", "AMGN", "HON", "PM", "SBUX", "MS", "CAT", "BA", "GE", "RTX",
]


async def get_sector_performance() -> dict:
    """Get performance data for all 11 GICS sectors."""
    cache_key = "sector_heatmap"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    sectors = []
    symbols = [s["symbol"] for s in SECTOR_ETFS]

    try:
        # Fetch all ETFs at once
        data = yf.download(
            " ".join(symbols),
            period="1mo",
            interval="1d",
            progress=False,
            group_by="ticker",
        )

        total_market_cap = 0
        sector_data = []

        for etf in SECTOR_ETFS:
            sym = etf["symbol"]
            try:
                if len(symbols) == 1:
                    closes = data["Close"].dropna()
                else:
                    closes = data[sym]["Close"].dropna()

                if len(closes) < 2:
                    continue

                # Performance calculations
                perf_1d = (closes.iloc[-1] / closes.iloc[-2] - 1) if len(closes) >= 2 else 0
                perf_1w = (closes.iloc[-1] / closes.iloc[-5] - 1) if len(closes) >= 5 else perf_1d
                perf_1m = (closes.iloc[-1] / closes.iloc[0] - 1) if len(closes) >= 2 else 0

                # Market cap weight from ETF info
                info = yf.Ticker(sym).info
                mcap = info.get("totalAssets", info.get("marketCap", 0)) or 0

                sector_data.append({
                    "symbol": sym,
                    "name": etf["name"],
                    "performance_1d": round(float(perf_1d), 4),
                    "performance_1w": round(float(perf_1w), 4),
                    "performance_1m": round(float(perf_1m), 4),
                    "raw_mcap": mcap,
                })
                total_market_cap += mcap
            except Exception as e:
                logger.debug("Failed to fetch sector %s: %s", sym, e)
                continue

        # Normalize weights
        for s in sector_data:
            s["market_cap_weight"] = round(s["raw_mcap"] / total_market_cap, 4) if total_market_cap > 0 else round(1.0 / len(sector_data), 4)
            del s["raw_mcap"]
            sectors.append(s)

    except Exception as e:
        logger.error("Sector heatmap fetch failed: %s", e)

    result = {
        "sectors": sectors,
        "last_updated": datetime.now().isoformat(),
    }

    if sectors:
        cache.set(cache_key, result, HEATMAP_TTL)

    return result


async def get_market_breadth() -> dict:
    """Calculate market breadth indicators."""
    cache_key = "market_breadth"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        data = yf.download(
            " ".join(BREADTH_STOCKS),
            period="1y",
            interval="1d",
            progress=False,
            group_by="ticker",
        )

        if data.empty:
            return _empty_breadth()

        advancing = 0
        declining = 0
        unchanged = 0
        above_sma50 = 0
        above_sma200 = 0
        new_highs = 0
        new_lows = 0
        total_valid = 0

        for sym in BREADTH_STOCKS:
            try:
                closes = data[sym]["Close"].dropna()
                if len(closes) < 50:
                    continue

                total_valid += 1
                current = closes.iloc[-1]
                prev = closes.iloc[-2]

                # Advancing/declining
                if current > prev * 1.0001:
                    advancing += 1
                elif current < prev * 0.9999:
                    declining += 1
                else:
                    unchanged += 1

                # SMA checks
                sma50 = closes.iloc[-50:].mean()
                if current > sma50:
                    above_sma50 += 1

                if len(closes) >= 200:
                    sma200 = closes.iloc[-200:].mean()
                    if current > sma200:
                        above_sma200 += 1

                # 52-week high/low
                high_52w = closes.iloc[-252:].max() if len(closes) >= 252 else closes.max()
                low_52w = closes.iloc[-252:].min() if len(closes) >= 252 else closes.min()

                if current >= high_52w * 0.98:
                    new_highs += 1
                if current <= low_52w * 1.02:
                    new_lows += 1

            except Exception:
                continue

        if total_valid == 0:
            return _empty_breadth()

        ad_ratio = advancing / declining if declining > 0 else advancing
        pct_50 = round(above_sma50 / total_valid, 4)
        pct_200 = round(above_sma200 / total_valid, 4)

        # Classify sentiment
        if ad_ratio > 1.5 and pct_50 > 0.6:
            sentiment = "bullish"
        elif ad_ratio < 0.67 and pct_50 < 0.4:
            sentiment = "bearish"
        else:
            sentiment = "neutral"

        result = {
            "advancing": advancing,
            "declining": declining,
            "unchanged": unchanged,
            "advance_decline_ratio": round(ad_ratio, 2),
            "new_highs": new_highs,
            "new_lows": new_lows,
            "pct_above_sma50": pct_50,
            "pct_above_sma200": pct_200,
            "sentiment": sentiment,
            "last_updated": datetime.now().isoformat(),
        }

        cache.set(cache_key, result, BREADTH_TTL)
        return result

    except Exception as e:
        logger.error("Market breadth calculation failed: %s", e)
        return _empty_breadth()


def _empty_breadth() -> dict:
    return {
        "advancing": 0, "declining": 0, "unchanged": 0,
        "advance_decline_ratio": 0, "new_highs": 0, "new_lows": 0,
        "pct_above_sma50": 0, "pct_above_sma200": 0,
        "sentiment": "neutral",
        "last_updated": datetime.now().isoformat(),
    }
