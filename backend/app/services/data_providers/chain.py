"""Provider chains for fallback and aggregation."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable

from app.services.data_providers.base import BaseDataProvider

logger = logging.getLogger(__name__)


def parse_provider_order(raw: str) -> list[str]:
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def order_providers(
    providers: Iterable[BaseDataProvider],
    order: list[str] | None = None,
) -> list[BaseDataProvider]:
    items = list(providers)
    if not order:
        return items

    by_id = {provider.provider_id.lower(): provider for provider in items}
    ordered: list[BaseDataProvider] = []
    seen: set[str] = set()

    for provider_id in order:
        provider = by_id.get(provider_id.lower())
        if provider:
            ordered.append(provider)
            seen.add(provider.provider_id.lower())

    for provider in items:
        key = provider.provider_id.lower()
        if key not in seen:
            ordered.append(provider)

    return ordered


class FallbackProviderChain:
    """Try providers in priority order until one returns data."""

    def __init__(self, name: str, providers: list[BaseDataProvider], order: list[str] | None = None):
        self.name = name
        self._providers = order_providers(providers, order)

    @property
    def providers(self) -> list[dict]:
        return [
            provider.describe(priority=index + 1)
            for index, provider in enumerate(self._providers)
        ]

    @property
    def active_providers(self) -> list[BaseDataProvider]:
        return [provider for provider in self._providers if provider.is_enabled]

    async def call_first(self, method_name: str, *args, **kwargs):
        for provider in self.active_providers:
            method = getattr(provider, method_name)
            try:
                result = await method(*args, **kwargs)
            except Exception as exc:
                logger.warning(
                    "%s provider %s failed on %s: %s",
                    self.name,
                    provider.provider_id,
                    method_name,
                    exc,
                )
                continue
            if result:
                return result
        return None

    async def close(self) -> None:
        for provider in self._providers:
            await provider.close()


class AggregatingProviderChain:
    """Fetch data from all active providers and flatten the results."""

    def __init__(self, name: str, providers: list[BaseDataProvider], order: list[str] | None = None):
        self.name = name
        self._providers = order_providers(providers, order)

    @property
    def providers(self) -> list[dict]:
        return [
            provider.describe(priority=index + 1)
            for index, provider in enumerate(self._providers)
        ]

    @property
    def active_providers(self) -> list[BaseDataProvider]:
        return [provider for provider in self._providers if provider.is_enabled]

    async def gather(self, method_name: str, *args, **kwargs) -> list[tuple[str, object]]:
        async def _run(provider: BaseDataProvider):
            method = getattr(provider, method_name)
            try:
                return provider.provider_id, await method(*args, **kwargs)
            except Exception as exc:
                logger.warning(
                    "%s provider %s failed on %s: %s",
                    self.name,
                    provider.provider_id,
                    method_name,
                    exc,
                )
                return provider.provider_id, []

        results = await asyncio.gather(
            *[_run(provider) for provider in self.active_providers],
            return_exceptions=False,
        )
        return list(results)

    async def close(self) -> None:
        for provider in self._providers:
            await provider.close()
