"""Compatibility helpers over the normalized SEC filings provider chain."""

from __future__ import annotations

from app.services.data_providers import filings_provider_chain
from app.services.data_providers.filings import _get_company_map
from app.services.data_providers.normalization import to_utc_iso


async def lookup_company(symbol: str) -> dict | None:
    companies = await _get_company_map()
    return companies.get(symbol.upper())


async def get_company_filings(symbol: str, limit: int = 10) -> dict:
    symbol_upper = symbol.upper()
    filings = await filings_provider_chain.get_filings(symbol_upper, limit=limit)
    if filings:
        return filings

    company = await lookup_company(symbol_upper)
    return {
        "symbol": symbol_upper,
        "company_name": company["name"] if company else symbol_upper,
        "cik": company["cik"] if company else "",
        "source": "SEC EDGAR",
        "source_provider": "sec",
        "retrieval_mode": "official_api",
        "filings": [],
        "generated_at": to_utc_iso(),
    }
