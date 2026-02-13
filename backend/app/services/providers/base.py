"""Abstract base class for market data providers."""

from abc import ABC, abstractmethod


class MarketDataProvider(ABC):
    """Interface for market data providers with fallback support."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Whether this provider has required credentials/setup."""

    @abstractmethod
    async def get_quote(self, symbol: str) -> dict | None:
        """Get current price quote for a symbol.

        Returns dict with: symbol, name, price, change_percent, volume, previous_close, market_cap
        or None if unavailable.
        """

    @abstractmethod
    async def get_history(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> list[dict]:
        """Get historical OHLCV data.

        Returns list of dicts with: date, open, high, low, close, volume
        """

    async def close(self) -> None:
        """Cleanup resources."""
        pass
