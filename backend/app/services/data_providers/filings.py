"""Regulatory filings providers and fallback chain."""

from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.services.cache import get_or_fetch
from app.services.data_providers.base import FilingsProvider
from app.services.data_providers.chain import FallbackProviderChain, parse_provider_order
from app.services.data_providers.normalization import normalize_filings_payload

logger = logging.getLogger(__name__)

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_TTL = 3600


def _sec_headers() -> dict[str, str]:
    return {
        "User-Agent": settings.sec_user_agent,
        "Accept-Encoding": "gzip, deflate",
        "Host": "www.sec.gov",
    }


async def _get_company_map() -> dict[str, dict]:
    async def _fetch():
        try:
            async with httpx.AsyncClient(timeout=12.0, headers=_sec_headers()) as client:
                response = await client.get(SEC_TICKERS_URL)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            logger.warning("SEC company map unavailable: %s", exc)
            return {}

        companies: dict[str, dict] = {}
        iterable = payload.values() if isinstance(payload, dict) else payload
        for item in iterable:
            symbol = str(item.get("ticker") or "").upper().strip()
            if not symbol:
                continue
            companies[symbol] = {
                "symbol": symbol,
                "name": str(item.get("title") or symbol),
                "cik": str(item.get("cik_str") or "").zfill(10),
            }
        return companies

    return await get_or_fetch("filings:sec:company-map", _fetch, 24 * SEC_TTL) or {}


class SECFilingsProvider(FilingsProvider):
    provider_id = "sec"
    display_name = "SEC EDGAR"
    retrieval_mode = "official_api"
    note = "Primary official filings provider"
    is_core = True
    is_free = True
    capabilities = ("filings",)

    @property
    def is_configured(self) -> bool:
        return True

    async def get_filings(self, symbol: str, limit: int = 10) -> dict | None:
        symbol_upper = symbol.upper()
        company = (await _get_company_map()).get(symbol_upper)
        if not company:
            return normalize_filings_payload(
                {
                    "symbol": symbol_upper,
                    "company_name": symbol_upper,
                    "cik": "",
                    "filings": [],
                },
                symbol=symbol_upper,
                provider_id=self.provider_id,
                provider_name=self.display_name,
                retrieval_mode=self.retrieval_mode,
            )

        async def _fetch():
            try:
                async with httpx.AsyncClient(timeout=15.0, headers=_sec_headers()) as client:
                    response = await client.get(
                        SEC_SUBMISSIONS_URL.format(cik=company["cik"])
                    )
                    response.raise_for_status()
                    payload = response.json()
            except Exception as exc:
                logger.warning("SEC filings unavailable for %s: %s", symbol_upper, exc)
                return None

            recent = payload.get("filings", {}).get("recent", {})
            forms = recent.get("form", []) or []
            dates = recent.get("filingDate", []) or []
            accessions = recent.get("accessionNumber", []) or []
            docs = recent.get("primaryDocument", []) or []
            descriptions = recent.get("primaryDocDescription", []) or []
            items = recent.get("items", []) or []

            filings = []
            for index, form in enumerate(forms[: max(limit * 2, limit)]):
                accession = str(accessions[index] or "")
                accession_slug = accession.replace("-", "")
                primary_doc = str(docs[index] or "")
                url = ""
                if accession_slug and primary_doc:
                    url = (
                        "https://www.sec.gov/Archives/edgar/data/"
                        f"{int(company['cik'])}/{accession_slug}/{primary_doc}"
                    )
                filings.append(
                    {
                        "form": str(form),
                        "filed_at": str(dates[index] or ""),
                        "description": str(descriptions[index] or form or ""),
                        "items": str(items[index] or ""),
                        "url": url,
                        "accession_number": accession,
                    }
                )

            filtered = [
                filing
                for filing in filings
                if filing["form"] in {"10-K", "10-Q", "8-K", "6-K", "20-F", "S-1", "424B2", "4"}
            ][:limit]
            return normalize_filings_payload(
                {
                    "symbol": symbol_upper,
                    "company_name": company["name"],
                    "cik": company["cik"],
                    "filings": filtered,
                },
                symbol=symbol_upper,
                provider_id=self.provider_id,
                provider_name=self.display_name,
                retrieval_mode=self.retrieval_mode,
            )

        return await get_or_fetch(f"filings:sec:{symbol_upper}", _fetch, SEC_TTL)


class FilingsProviderChain(FallbackProviderChain):
    def __init__(self):
        super().__init__(
            "filings",
            [SECFilingsProvider()],
            parse_provider_order(settings.filings_provider_order),
        )

    async def get_filings(self, symbol: str, limit: int = 10) -> dict | None:
        return await self.call_first("get_filings", symbol, limit)


filings_provider_chain = FilingsProviderChain()
