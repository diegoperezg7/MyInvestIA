"""Base interfaces for normalized data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    id: str
    name: str
    domain: str
    configured: bool
    enabled: bool
    priority: int
    is_core: bool
    is_free: bool
    retrieval_mode: str
    note: str = ""
    capabilities: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "configured": self.configured,
            "enabled": self.enabled,
            "priority": self.priority,
            "core": self.is_core,
            "free_tier": self.is_free,
            "retrieval_mode": self.retrieval_mode,
            "note": self.note,
            "capabilities": list(self.capabilities),
        }


class BaseDataProvider(ABC):
    """Common metadata and lifecycle interface for all providers."""

    provider_id: str = "provider"
    display_name: str = "Provider"
    domain: str = "generic"
    retrieval_mode: str = "unknown"
    note: str = ""
    is_core: bool = False
    is_free: bool = True
    capabilities: tuple[str, ...] = ()

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Whether the provider can currently be used."""

    @property
    def is_enabled(self) -> bool:
        return self.is_configured

    def describe(self, priority: int) -> dict:
        return ProviderDescriptor(
            id=self.provider_id,
            name=self.display_name,
            domain=self.domain,
            configured=self.is_configured,
            enabled=self.is_enabled,
            priority=priority,
            is_core=self.is_core,
            is_free=self.is_free,
            retrieval_mode=self.retrieval_mode,
            note=self.note,
            capabilities=self.capabilities,
        ).to_dict()

    async def close(self) -> None:
        """Allow providers to cleanup resources."""
        return None


class MarketProvider(BaseDataProvider):
    domain = "market"

    @abstractmethod
    async def get_quote(self, symbol: str) -> dict | None:
        """Return a normalized quote payload or None."""

    @abstractmethod
    async def get_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[dict]:
        """Return normalized OHLCV rows."""

    async def get_quotes_batch(self, symbols: list[str]) -> dict[str, dict]:
        return {}


class CryptoProvider(BaseDataProvider):
    domain = "crypto"

    @abstractmethod
    async def get_quote(self, symbol: str) -> dict | None:
        """Return a normalized crypto quote payload or None."""

    @abstractmethod
    async def get_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[dict]:
        """Return normalized crypto OHLCV rows."""

    async def get_market_chart(self, symbol: str, days: int = 30) -> list[dict]:
        return []


class MacroProvider(BaseDataProvider):
    domain = "macro"

    @abstractmethod
    async def get_indicators(self) -> list[dict]:
        """Return normalized macro indicators."""


class FundamentalsProvider(BaseDataProvider):
    domain = "fundamentals"

    @abstractmethod
    async def get_fundamentals(self, symbol: str) -> dict | None:
        """Return normalized fundamentals payload or None."""


class FilingsProvider(BaseDataProvider):
    domain = "filings"

    @abstractmethod
    async def get_filings(self, symbol: str, limit: int = 10) -> dict | None:
        """Return normalized filings payload or None."""


class NewsProvider(BaseDataProvider):
    domain = "news"

    @abstractmethod
    async def fetch(self, limit: int = 15) -> list[dict]:
        """Return normalized news items."""
