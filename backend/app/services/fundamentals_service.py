"""Compatibility facade over the normalized fundamentals provider chain."""

from __future__ import annotations

from app.services.data_providers import fundamentals_provider_chain


async def get_fundamentals(symbol: str) -> dict | None:
    return await fundamentals_provider_chain.get_fundamentals(symbol.upper())
