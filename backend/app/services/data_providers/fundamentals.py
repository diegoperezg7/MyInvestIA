"""Fundamentals providers and fallback chain."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import yfinance as yf

from app.config import settings
from app.services import cache
from app.services.data_providers.base import FundamentalsProvider
from app.services.data_providers.chain import FallbackProviderChain, parse_provider_order
from app.services.data_providers.normalization import normalize_fundamentals_payload

logger = logging.getLogger(__name__)

FUNDAMENTALS_TTL = 86400

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


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _compute_growth(ticker: yf.Ticker) -> dict:
    try:
        income = ticker.income_stmt
        if income is None or income.empty:
            return {"revenue_growth": 0, "earnings_growth": 0, "revenue_history": [], "earnings_history": []}

        periods = [str(column.date()) for column in income.columns[:4]]
        revenues = []
        net_income = []
        for column in income.columns[:4]:
            revenues.append(_safe_float(income[column].get("Total Revenue", 0)))
            net_income.append(_safe_float(income[column].get("Net Income", 0)))

        revenue_growth = 0.0
        if len(revenues) >= 2 and revenues[1] != 0:
            revenue_growth = (revenues[0] - revenues[1]) / abs(revenues[1])

        earnings_growth = 0.0
        if len(net_income) >= 2 and net_income[1] != 0:
            earnings_growth = (net_income[0] - net_income[1]) / abs(net_income[1])

        return {
            "revenue_growth": round(revenue_growth, 4),
            "earnings_growth": round(earnings_growth, 4),
            "revenue_history": [
                {"period": period, "value": value}
                for period, value in zip(periods, revenues)
            ],
            "earnings_history": [
                {"period": period, "value": value}
                for period, value in zip(periods, net_income)
            ],
        }
    except Exception as exc:
        logger.debug("Fundamentals growth computation failed: %s", exc)
        return {"revenue_growth": 0, "earnings_growth": 0, "revenue_history": [], "earnings_history": []}


async def _get_peer_comparison(symbol: str, sector: str) -> list[dict]:
    peer_symbols = [item for item in SECTOR_PEERS.get(sector, []) if item != symbol][:5]
    if not peer_symbols:
        return []

    peers = []
    for peer_symbol in peer_symbols:
        cache_key = f"fundamentals:peer:{peer_symbol}"
        cached = cache.get(cache_key)
        if cached is not None:
            peers.append(cached)
            continue
        try:
            info = yf.Ticker(peer_symbol).info or {}
        except Exception:
            continue
        payload = {
            "symbol": peer_symbol,
            "name": info.get("shortName", peer_symbol),
            "pe_trailing": _safe_float(info.get("trailingPE")),
            "price_to_book": _safe_float(info.get("priceToBook")),
            "roe": _safe_float(info.get("returnOnEquity")),
            "profit_margins": _safe_float(info.get("profitMargins")),
            "market_cap": _safe_float(info.get("marketCap")),
        }
        cache.set(cache_key, payload, FUNDAMENTALS_TTL)
        peers.append(payload)
    return peers


class YFinanceFundamentalsProvider(FundamentalsProvider):
    provider_id = "yfinance"
    display_name = "Yahoo Finance"
    retrieval_mode = "library"
    note = "Primary free fundamentals provider"
    is_core = True
    is_free = True
    capabilities = ("fundamentals",)

    @property
    def is_configured(self) -> bool:
        return True

    async def get_fundamentals(self, symbol: str) -> dict | None:
        symbol_upper = symbol.upper()
        cache_key = f"fundamentals:{symbol_upper}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            ticker = await asyncio.to_thread(yf.Ticker, symbol_upper)
            info = ticker.info or {}
        except Exception as exc:
            logger.warning("Yahoo Finance fundamentals failed for %s: %s", symbol_upper, exc)
            return None

        if not info.get("shortName"):
            return None

        payload = {
            "symbol": symbol_upper,
            "company_info": {
                "name": info.get("shortName", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "market_cap": _safe_float(info.get("marketCap")),
                "employees": info.get("fullTimeEmployees"),
                "description": (info.get("longBusinessSummary") or "")[:300],
                "website": info.get("website", ""),
                "country": info.get("country", ""),
            },
            "ratios": {
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
            },
            "growth": _compute_growth(ticker),
            "peers": await _get_peer_comparison(symbol_upper, info.get("sector", "")),
        }
        normalized = normalize_fundamentals_payload(
            payload,
            symbol=symbol_upper,
            provider_id=self.provider_id,
            provider_name=self.display_name,
            retrieval_mode=self.retrieval_mode,
        )
        cache.set(cache_key, normalized, FUNDAMENTALS_TTL)
        return normalized


class FundamentalsProviderChain(FallbackProviderChain):
    def __init__(self):
        super().__init__(
            "fundamentals",
            [YFinanceFundamentalsProvider()],
            parse_provider_order(settings.fundamentals_provider_order),
        )

    async def get_fundamentals(self, symbol: str) -> dict | None:
        return await self.call_first("get_fundamentals", symbol)


fundamentals_provider_chain = FundamentalsProviderChain()
