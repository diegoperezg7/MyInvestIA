"""Market data providers and fallback chain."""

from __future__ import annotations

from app.config import settings
from app.services.data_providers.base import MarketProvider
from app.services.data_providers.chain import FallbackProviderChain, parse_provider_order
from app.services.data_providers.normalization import (
    normalize_history_rows,
    normalize_quote_payload,
)
from app.services.providers.alphavantage_provider import AlphaVantageProvider as LegacyAlphaVantageProvider
from app.services.providers.finnhub_provider import FinnhubProvider as LegacyFinnhubProvider
from app.services.providers.twelvedata_provider import TwelveDataProvider as LegacyTwelveDataProvider
from app.services.providers.yfinance_provider import YFinanceProvider as LegacyYFinanceProvider

try:
    from app.services.providers.bloomberg_provider import BloombergProvider as LegacyBloombergProvider
except Exception:
    LegacyBloombergProvider = None


COMMODITY_FUTURES_MAP: dict[str, dict] = {
    "GOLD": {"ticker": "GC=F", "name": "Gold", "category": "metals"},
    "SILVER": {"ticker": "SI=F", "name": "Silver", "category": "metals"},
    "PLATINUM": {"ticker": "PL=F", "name": "Platinum", "category": "metals"},
    "PALLADIUM": {"ticker": "PA=F", "name": "Palladium", "category": "metals"},
    "COPPER": {"ticker": "HG=F", "name": "Copper", "category": "metals"},
    "OIL": {"ticker": "CL=F", "name": "Crude Oil WTI", "category": "energy"},
    "BRENT": {"ticker": "BZ=F", "name": "Brent Crude", "category": "energy"},
    "NATGAS": {"ticker": "NG=F", "name": "Natural Gas", "category": "energy"},
    "WHEAT": {"ticker": "ZW=F", "name": "Wheat", "category": "agriculture"},
    "CORN": {"ticker": "ZC=F", "name": "Corn", "category": "agriculture"},
    "SOYBEAN": {"ticker": "ZS=F", "name": "Soybeans", "category": "agriculture"},
    "COFFEE": {"ticker": "KC=F", "name": "Coffee", "category": "agriculture"},
    "SUGAR": {"ticker": "SB=F", "name": "Sugar", "category": "agriculture"},
    "COCOA": {"ticker": "CC=F", "name": "Cocoa", "category": "agriculture"},
    "COTTON": {"ticker": "CT=F", "name": "Cotton", "category": "agriculture"},
    "CATTLE": {"ticker": "LE=F", "name": "Live Cattle", "category": "agriculture"},
}


class LegacyMarketProviderAdapter(MarketProvider):
    """Wrap the existing market provider implementations with normalized outputs."""

    def __init__(
        self,
        legacy_provider,
        *,
        provider_id: str,
        display_name: str,
        retrieval_mode: str,
        is_core: bool,
        is_free: bool,
        note: str,
    ):
        self._provider = legacy_provider
        self.provider_id = provider_id
        self.display_name = display_name
        self.retrieval_mode = retrieval_mode
        self.is_core = is_core
        self.is_free = is_free
        self.note = note
        self.capabilities = ("quote", "history")
        if hasattr(legacy_provider, "get_quotes_batch"):
            self.capabilities = ("quote", "history", "batch_quotes")

    @property
    def is_configured(self) -> bool:
        return bool(self._provider.is_configured)

    async def get_quote(self, symbol: str) -> dict | None:
        raw = await self._provider.get_quote(symbol)
        return normalize_quote_payload(
            raw,
            symbol=symbol,
            provider_id=self.provider_id,
            provider_name=self.display_name,
            retrieval_mode=self.retrieval_mode,
        )

    async def get_quotes_batch(self, symbols: list[str]) -> dict[str, dict]:
        if not hasattr(self._provider, "get_quotes_batch"):
            return {}
        raw = await self._provider.get_quotes_batch(symbols)
        results: dict[str, dict] = {}
        for symbol, quote in (raw or {}).items():
            normalized = normalize_quote_payload(
                quote,
                symbol=symbol,
                provider_id=self.provider_id,
                provider_name=self.display_name,
                retrieval_mode=self.retrieval_mode,
            )
            if normalized:
                results[symbol.upper()] = normalized
        return results

    async def get_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[dict]:
        rows = await self._provider.get_history(symbol, period, interval)
        return normalize_history_rows(
            rows,
            provider_id=self.provider_id,
            retrieval_mode=self.retrieval_mode,
        )

    async def close(self) -> None:
        await self._provider.close()


def _build_market_providers() -> list[MarketProvider]:
    providers: list[MarketProvider] = [
        LegacyMarketProviderAdapter(
            LegacyYFinanceProvider(),
            provider_id="yfinance",
            display_name="Yahoo Finance",
            retrieval_mode="library",
            is_core=True,
            is_free=True,
            note="Primary free market data provider",
        ),
        LegacyMarketProviderAdapter(
            LegacyAlphaVantageProvider(),
            provider_id="alphavantage",
            display_name="Alpha Vantage",
            retrieval_mode="developer_api",
            is_core=False,
            is_free=True,
            note="Optional fallback with free API tier",
        ),
        LegacyMarketProviderAdapter(
            LegacyFinnhubProvider(),
            provider_id="finnhub",
            display_name="Finnhub",
            retrieval_mode="developer_api",
            is_core=False,
            is_free=True,
            note="Optional fallback with free API tier",
        ),
        LegacyMarketProviderAdapter(
            LegacyTwelveDataProvider(),
            provider_id="twelvedata",
            display_name="Twelve Data",
            retrieval_mode="developer_api",
            is_core=False,
            is_free=True,
            note="Optional fallback with free API tier",
        ),
    ]
    if settings.bloomberg_enabled and LegacyBloombergProvider is not None:
        providers.insert(
            1,
            LegacyMarketProviderAdapter(
                LegacyBloombergProvider(),
                provider_id="bloomberg",
                display_name="Bloomberg",
                retrieval_mode="terminal_gateway",
                is_core=False,
                is_free=False,
                note="Paid provider kept isolated and optional",
            ),
        )
    return providers


class MarketProviderChain(FallbackProviderChain):
    def __init__(self):
        super().__init__(
            "market",
            _build_market_providers(),
            parse_provider_order(settings.market_provider_order),
        )

    async def get_quote(self, symbol: str) -> dict | None:
        return await self.call_first("get_quote", symbol)

    async def get_quotes_batch(self, symbols: list[str]) -> dict[str, dict]:
        for provider in self.active_providers:
            if "batch_quotes" not in provider.capabilities:
                continue
            results = await provider.get_quotes_batch(symbols)
            if results:
                missing = [symbol for symbol in symbols if symbol.upper() not in results]
                for symbol in missing:
                    quote = await self.get_quote(symbol)
                    if quote:
                        results[symbol.upper()] = quote
                return results
        results: dict[str, dict] = {}
        for symbol in symbols:
            quote = await self.get_quote(symbol)
            if quote:
                results[symbol.upper()] = quote
        return results

    async def get_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[dict]:
        return await self.call_first("get_history", symbol, period, interval) or []


market_provider_chain = MarketProviderChain()
