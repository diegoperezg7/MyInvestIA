"""Compatibility facade over the normalized market provider chain."""

from __future__ import annotations

from app.services.data_providers import market_provider_chain


def _with_legacy_provider_alias(payload: dict | None) -> dict | None:
    if not payload:
        return None
    result = dict(payload)
    result.setdefault("provider", result.get("source", ""))
    return result


class ProviderChain:
    """Expose the historical provider-chain API while delegating to the new layer."""

    @property
    def providers(self) -> list[dict]:
        return market_provider_chain.providers

    @property
    def active_providers(self) -> list:
        return market_provider_chain.active_providers

    async def get_quote(self, symbol: str) -> dict | None:
        return _with_legacy_provider_alias(
            await market_provider_chain.get_quote(symbol)
        )

    async def get_quotes_batch(self, symbols: list[str]) -> dict[str, dict]:
        results = await market_provider_chain.get_quotes_batch(symbols)
        return {
            key: _with_legacy_provider_alias(value) or {}
            for key, value in results.items()
            if value
        }

    async def get_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[dict]:
        return await market_provider_chain.get_history(symbol, period, interval)

    async def close(self) -> None:
        await market_provider_chain.close()


provider_chain = ProviderChain()
