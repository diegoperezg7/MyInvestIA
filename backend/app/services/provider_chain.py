"""Market data provider chain with automatic fallback.

Tries providers in order until one succeeds. Primary provider is
always tried first (Yahoo Finance), with optional paid providers
as fallbacks.
"""

import logging

from app.services.providers.base import MarketDataProvider
from app.services.providers.yfinance_provider import YFinanceProvider
from app.services.providers.alphavantage_provider import AlphaVantageProvider
from app.services.providers.finnhub_provider import FinnhubProvider
from app.services.providers.twelvedata_provider import TwelveDataProvider

try:
    from app.services.providers.bloomberg_provider import BloombergProvider
except ImportError:
    BloombergProvider = None

logger = logging.getLogger(__name__)


class ProviderChain:
    """Orchestrates multiple market data providers with fallback."""

    def __init__(self):
        self._providers: list[MarketDataProvider] = [
            YFinanceProvider(),
            BloombergProvider() if BloombergProvider else None,
            AlphaVantageProvider(),
            FinnhubProvider(),
            TwelveDataProvider(),
        ]
        self._providers = [p for p in self._providers if p is not None]

    @property
    def providers(self) -> list[dict]:
        """Return status of all providers."""
        return [
            {
                "name": p.name,
                "configured": p.is_configured,
                "priority": i + 1,
            }
            for i, p in enumerate(self._providers)
        ]

    @property
    def active_providers(self) -> list[MarketDataProvider]:
        """Return only configured providers."""
        return [p for p in self._providers if p.is_configured]

    async def get_quote(self, symbol: str) -> dict | None:
        """Try each provider in order until one returns a quote."""
        for provider in self.active_providers:
            try:
                result = await provider.get_quote(symbol)
                if result:
                    result["provider"] = provider.name
                    return result
            except Exception as e:
                logger.warning(
                    "Provider %s failed for quote %s: %s",
                    provider.name,
                    symbol,
                    e,
                )
                continue
        return None

    async def get_quotes_batch(self, symbols: list[str]) -> dict[str, dict]:
        """Batch-fetch quotes. Uses yfinance batch if available, falls back to individual calls."""
        # Try YFinanceProvider batch first (it's always first and always configured)
        for provider in self.active_providers:
            if hasattr(provider, "get_quotes_batch"):
                try:
                    results = await provider.get_quotes_batch(symbols)
                    # Tag with provider name
                    for sym in results:
                        results[sym]["provider"] = provider.name
                    # Fall back to individual calls for any symbols that failed
                    missing = [s for s in symbols if s.upper() not in results]
                    if missing:
                        for sym in missing:
                            quote = await self.get_quote(sym)
                            if quote:
                                results[sym.upper()] = quote
                    return results
                except Exception as e:
                    logger.warning("Batch fetch failed on %s: %s", provider.name, e)

        # Fallback: individual calls for all symbols
        results = {}
        for sym in symbols:
            quote = await self.get_quote(sym)
            if quote:
                results[sym.upper()] = quote
        return results

    async def get_history(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> list[dict]:
        """Try each provider in order until one returns history data."""
        for provider in self.active_providers:
            try:
                result = await provider.get_history(symbol, period, interval)
                if result:
                    return result
            except Exception as e:
                logger.warning(
                    "Provider %s failed for history %s: %s",
                    provider.name,
                    symbol,
                    e,
                )
                continue
        return []

    async def close(self) -> None:
        """Close all providers."""
        for provider in self._providers:
            await provider.close()


# Singleton
provider_chain = ProviderChain()
