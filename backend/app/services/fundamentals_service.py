"""Fundamentals data service using yfinance."""

import logging
from typing import Any

import yfinance as yf

from app.services import cache

logger = logging.getLogger(__name__)

FUNDAMENTALS_TTL = 86400  # 24 hours

# Sector → representative peer symbols
SECTOR_PEERS: dict[str, list[str]] = {
    "Technology": ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "CRM", "ADBE"],
    "Financial Services": ["JPM", "BAC", "GS", "MS", "WFC", "BLK", "SCHW"],
    "Healthcare": ["UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD", "NKE", "MCD", "SBUX", "BKNG"],
    "Consumer Defensive": ["WMT", "PG", "KO", "PEP", "COST", "CL", "PM"],
    "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "CMCSA", "T", "VZ"],
    "Industrials": ["CAT", "HON", "BA", "GE", "RTX", "LMT", "DE"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "OXY", "MPC"],
    "Basic Materials": ["LIN", "SHW", "FCX", "NEM", "NUE", "DOW", "APD"],
    "Real Estate": ["AMT", "PLD", "CCI", "EQIX", "SPG", "O", "DLR"],
    "Utilities": ["NEE", "DUK", "SO", "D", "AEP", "SRE", "EXC"],
}


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


async def get_fundamentals(symbol: str) -> dict | None:
    """Get fundamental data for a symbol."""
    cache_key = f"fundamentals:{symbol.upper()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}

        if not info.get("shortName"):
            return None

        company_info = {
            "name": info.get("shortName", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "market_cap": _safe_float(info.get("marketCap")),
            "employees": info.get("fullTimeEmployees"),
            "description": (info.get("longBusinessSummary") or "")[:300],
            "website": info.get("website", ""),
            "country": info.get("country", ""),
        }

        ratios = {
            "pe_trailing": _safe_float(info.get("trailingPE")),
            "pe_forward": _safe_float(info.get("forwardPE")),
            "price_to_book": _safe_float(info.get("priceToBook")),
            "price_to_sales": _safe_float(info.get("priceToSalesTrailing12Months")),
            "ev_to_ebitda": _safe_float(info.get("enterpriseToEbitda")),
            "roe": _safe_float(info.get("returnOnEquity")),
            "debt_to_equity": _safe_float(info.get("debtToEquity")),
            "current_ratio": _safe_float(info.get("currentRatio")),
            "profit_margins": _safe_float(info.get("profitMargins")),
            "operating_margins": _safe_float(info.get("operatingMargins")),
            "gross_margins": _safe_float(info.get("grossMargins")),
            "dividend_yield": _safe_float(info.get("dividendYield")),
            "payout_ratio": _safe_float(info.get("payoutRatio")),
            "beta": _safe_float(info.get("beta")),
        }

        # Growth metrics from income statement
        growth = _compute_growth(ticker)

        # Peer comparison
        sector = info.get("sector", "")
        peers = await _get_peer_comparison(symbol.upper(), sector)

        result = {
            "symbol": symbol.upper(),
            "company_info": company_info,
            "ratios": ratios,
            "growth": growth,
            "peers": peers,
        }

        cache.set(cache_key, result, FUNDAMENTALS_TTL)
        return result

    except Exception as e:
        logger.error("Failed to get fundamentals for %s: %s", symbol, e)
        return None


def _compute_growth(ticker: yf.Ticker) -> dict:
    """Compute YoY revenue and earnings growth."""
    try:
        income = ticker.income_stmt
        if income is None or income.empty:
            return {"revenue_growth": 0, "earnings_growth": 0, "periods": []}

        # income_stmt columns are dates, rows are items
        periods = [str(c.date()) for c in income.columns[:4]]

        revenues = []
        net_income = []
        for col in income.columns[:4]:
            rev = income[col].get("Total Revenue", 0)
            ni = income[col].get("Net Income", 0)
            revenues.append(_safe_float(rev))
            net_income.append(_safe_float(ni))

        rev_growth = 0.0
        if len(revenues) >= 2 and revenues[1] != 0:
            rev_growth = (revenues[0] - revenues[1]) / abs(revenues[1])

        earn_growth = 0.0
        if len(net_income) >= 2 and net_income[1] != 0:
            earn_growth = (net_income[0] - net_income[1]) / abs(net_income[1])

        return {
            "revenue_growth": round(rev_growth, 4),
            "earnings_growth": round(earn_growth, 4),
            "revenue_history": [{"period": p, "value": v} for p, v in zip(periods, revenues)],
            "earnings_history": [{"period": p, "value": v} for p, v in zip(periods, net_income)],
        }
    except Exception as e:
        logger.debug("Growth computation failed: %s", e)
        return {"revenue_growth": 0, "earnings_growth": 0, "revenue_history": [], "earnings_history": []}


async def _get_peer_comparison(symbol: str, sector: str) -> list[dict]:
    """Get peer comparison data for the same sector."""
    peer_symbols = SECTOR_PEERS.get(sector, [])[:6]
    # Remove the symbol itself from peers
    peer_symbols = [s for s in peer_symbols if s != symbol][:5]

    if not peer_symbols:
        return []

    peers = []
    for sym in peer_symbols:
        peer_cache_key = f"peer_ratios:{sym}"
        cached = cache.get(peer_cache_key)
        if cached is not None:
            peers.append(cached)
            continue

        try:
            info = yf.Ticker(sym).info or {}
            peer_data = {
                "symbol": sym,
                "name": info.get("shortName", sym),
                "pe_trailing": _safe_float(info.get("trailingPE")),
                "price_to_book": _safe_float(info.get("priceToBook")),
                "roe": _safe_float(info.get("returnOnEquity")),
                "profit_margins": _safe_float(info.get("profitMargins")),
                "market_cap": _safe_float(info.get("marketCap")),
            }
            cache.set(peer_cache_key, peer_data, FUNDAMENTALS_TTL)
            peers.append(peer_data)
        except Exception:
            continue

    return peers
