"""Macro providers and merge-first chain."""

from __future__ import annotations

import asyncio
import logging
import time

import httpx
import yfinance as yf

from app.config import settings
from app.services.cache import MACRO_TTL, get_or_fetch
from app.services.data_providers.base import MacroProvider
from app.services.data_providers.chain import order_providers, parse_provider_order
from app.services.data_providers.normalization import normalize_macro_indicator

logger = logging.getLogger(__name__)

MACRO_SERIES = {
    "vix": {
        "name": "VIX (Volatility Index)",
        "ticker": "^VIX",
        "category": "volatility",
        "yfinance": "^VIX",
        "fred": "VIXCLS",
    },
    "dxy": {
        "name": "US Dollar Index (DXY)",
        "ticker": "DX-Y.NYB",
        "category": "currency",
        "yfinance": "DX-Y.NYB",
        "fred": "DTWEXBGS",
    },
    "10y": {
        "name": "10-Year Treasury Yield",
        "ticker": "^TNX",
        "category": "rates",
        "yfinance": "^TNX",
        "fred": "DGS10",
    },
    "3m": {
        "name": "13-Week T-Bill Rate",
        "ticker": "^IRX",
        "category": "rates",
        "yfinance": "^IRX",
        "fred": "DGS3MO",
    },
    "gold": {
        "name": "Gold Futures",
        "ticker": "GC=F",
        "category": "commodities",
        "yfinance": "GC=F",
        "fred": "GOLDAMGBD228NLBM",
    },
    "silver": {
        "name": "Silver Futures",
        "ticker": "SI=F",
        "category": "commodities",
        "yfinance": "SI=F",
        "fred": "",
    },
    "oil": {
        "name": "Crude Oil WTI",
        "ticker": "CL=F",
        "category": "commodities",
        "yfinance": "CL=F",
        "fred": "DCOILWTICO",
    },
    "natgas": {
        "name": "Natural Gas",
        "ticker": "NG=F",
        "category": "commodities",
        "yfinance": "NG=F",
        "fred": "DHHNGSP",
    },
    "copper": {
        "name": "Copper Futures",
        "ticker": "HG=F",
        "category": "commodities",
        "yfinance": "HG=F",
        "fred": "PCOPPUSDM",
    },
}

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"


def _get_trend(change_pct: float) -> str:
    if change_pct > 0.3:
        return "up"
    if change_pct < -0.3:
        return "down"
    return "stable"


def _vix_impact(value: float) -> str:
    if value >= 30:
        return "Extreme fear — markets highly volatile, risk-off environment"
    if value >= 20:
        return "Elevated volatility — uncertainty rising, consider defensive positioning"
    if value >= 15:
        return "Normal volatility — balanced risk environment"
    return "Low volatility — complacency, markets calm"


def _dxy_impact(change_pct: float) -> str:
    if change_pct > 0.5:
        return "Dollar strengthening — headwind for commodities and EM assets"
    if change_pct < -0.5:
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
        if change_pct < -1.0:
            return "Gold declining — risk-on sentiment, reduced inflation fears"
        return "Gold stable — balanced macro outlook"
    if "Silver" in name:
        if change_pct > 1.5:
            return "Silver rallying — industrial + safe-haven demand increasing"
        if change_pct < -1.5:
            return "Silver declining — reduced industrial demand or risk-on shift"
        return f"Silver {direction} — tracking precious metals complex"
    if "Oil" in name or "Crude" in name:
        if change_pct > 2.0:
            return "Oil surging — inflation risk, energy cost pressure"
        if change_pct < -2.0:
            return "Oil dropping — deflationary signal, demand concerns"
        return f"Oil {direction} — neutral energy market"
    if "Natural Gas" in name:
        if change_pct > 3.0:
            return "Natural gas spiking — supply concerns, utility cost pressure"
        if change_pct < -3.0:
            return "Natural gas plunging — oversupply or mild weather outlook"
        return f"Natural gas {direction} — normal seasonal movement"
    if "Copper" in name:
        if change_pct > 1.0:
            return "Copper rising — signal of industrial expansion and economic growth"
        if change_pct < -1.0:
            return "Copper falling — potential economic slowdown signal (Dr. Copper)"
        return f"Copper {direction} — neutral industrial demand"
    return f"{name} {direction}"


def _impact_description(name: str, ticker: str, category: str, value: float, change_pct: float) -> str:
    if "VIX" in ticker:
        return _vix_impact(value)
    if "DX-Y" in ticker:
        return _dxy_impact(change_pct)
    if category == "rates":
        return _yield_impact(value, change_pct)
    return _commodity_impact(name, change_pct)


class FREDMacroProvider(MacroProvider):
    provider_id = "fred"
    display_name = "FRED"
    retrieval_mode = "official_api"
    note = "Primary official macro source when series are available"
    is_core = True
    is_free = True
    capabilities = ("macro",)

    @property
    def is_configured(self) -> bool:
        return True

    async def get_indicators(self) -> list[dict]:
        async def _fetch():
            params_base = {"file_type": "json", "sort_order": "desc", "limit": 2}
            if settings.fred_api_key:
                params_base["api_key"] = settings.fred_api_key

            async with httpx.AsyncClient(timeout=12.0) as client:
                indicators = []
                for series in MACRO_SERIES.values():
                    fred_id = series.get("fred")
                    if not fred_id:
                        continue
                    try:
                        response = await client.get(
                            FRED_URL,
                            params={**params_base, "series_id": fred_id},
                        )
                        response.raise_for_status()
                        observations = response.json().get("observations", [])
                    except Exception as exc:
                        logger.debug("FRED macro series %s unavailable: %s", fred_id, exc)
                        continue

                    values = [
                        item
                        for item in observations
                        if item.get("value") not in {"", ".", None}
                    ]
                    if not values:
                        continue
                    current = float(values[0]["value"])
                    previous = float(values[1]["value"]) if len(values) > 1 else current
                    change_pct = ((current - previous) / previous * 100) if previous else 0.0
                    trend = _get_trend(change_pct)
                    indicators.append(
                        normalize_macro_indicator(
                            name=series["name"],
                            ticker=series["ticker"],
                            value=current,
                            previous_close=previous,
                            category=series["category"],
                            trend=trend,
                            impact_description=_impact_description(
                                series["name"],
                                series["ticker"],
                                series["category"],
                                current,
                                change_pct,
                            ),
                            provider_id=self.provider_id,
                            provider_name=self.display_name,
                            retrieval_mode=self.retrieval_mode,
                            as_of=values[0].get("date"),
                        )
                    )
                return [item for item in indicators if item]

        return await get_or_fetch("macro:provider:fred", _fetch, MACRO_TTL) or []


class YFinanceMacroProvider(MacroProvider):
    provider_id = "yfinance"
    display_name = "Yahoo Finance"
    retrieval_mode = "library"
    note = "Free fallback for market-derived macro proxies"
    is_core = True
    is_free = True
    capabilities = ("macro",)

    @property
    def is_configured(self) -> bool:
        return True

    async def get_indicators(self) -> list[dict]:
        async def _fetch():
            return await asyncio.to_thread(_sync_batch_fetch_macro)

        return await get_or_fetch("macro:provider:yfinance", _fetch, MACRO_TTL) or []


def _sync_batch_fetch_macro() -> list[dict]:
    tickers = [series["yfinance"] for series in MACRO_SERIES.values() if series.get("yfinance")]
    try:
        dataframe = yf.download(
            tickers,
            period="5d",
            interval="1d",
            group_by="ticker",
            progress=False,
            threads=False,
        )
    except Exception as exc:
        logger.warning("Yahoo Finance macro batch failed: %s", exc)
        return []

    if dataframe.empty:
        return []

    indicators = []
    for series in MACRO_SERIES.values():
        ticker = series.get("yfinance")
        if not ticker:
            continue
        try:
            ticker_df = dataframe if len(tickers) == 1 else dataframe[ticker]
            ticker_df = ticker_df.dropna(subset=["Close"])
            if len(ticker_df) < 1:
                continue
            current = float(ticker_df["Close"].iloc[-1])
            previous = float(ticker_df["Close"].iloc[-2]) if len(ticker_df) >= 2 else current
        except Exception as exc:
            logger.debug("Yahoo Finance macro extract failed for %s: %s", ticker, exc)
            continue

        change_pct = ((current - previous) / previous * 100) if previous else 0.0
        indicators.append(
            normalize_macro_indicator(
                name=series["name"],
                ticker=series["ticker"],
                value=current,
                previous_close=previous,
                category=series["category"],
                trend=_get_trend(change_pct),
                impact_description=_impact_description(
                    series["name"],
                    series["ticker"],
                    series["category"],
                    current,
                    change_pct,
                ),
                provider_id="yfinance",
                provider_name="Yahoo Finance",
                retrieval_mode="library",
                as_of=time.time(),
            )
        )
    return [item for item in indicators if item]


class MacroProviderChain:
    def __init__(self):
        providers = order_providers(
            [FREDMacroProvider(), YFinanceMacroProvider()],
            parse_provider_order(settings.macro_provider_order),
        )
        self._providers = providers

    @property
    def providers(self) -> list[dict]:
        return [
            provider.describe(priority=index + 1)
            for index, provider in enumerate(self._providers)
        ]

    @property
    def active_providers(self) -> list[MacroProvider]:
        return [provider for provider in self._providers if provider.is_enabled]

    async def get_indicators(self) -> list[dict]:
        merged: dict[str, dict] = {}
        for provider in self.active_providers:
            try:
                items = await provider.get_indicators()
            except Exception as exc:
                logger.warning("Macro provider %s failed: %s", provider.provider_id, exc)
                continue
            for item in items:
                ticker = str(item.get("ticker") or "")
                if ticker and ticker not in merged:
                    merged[ticker] = item
        return list(merged.values())

    async def close(self) -> None:
        for provider in self._providers:
            await provider.close()


macro_provider_chain = MacroProviderChain()
