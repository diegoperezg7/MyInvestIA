"""Insider activity service using Alpha Vantage when available with SEC fallback."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.services.cache import get_or_fetch
from app.services.sec_service import get_company_filings

logger = logging.getLogger(__name__)

ALPHAVANTAGE_URL = "https://www.alphavantage.co/query"
INSIDER_TTL = 3600


async def get_insider_activity(symbol: str, limit: int = 10) -> dict:
    symbol_upper = symbol.upper()

    async def _fetch():
        if settings.alphavantage_api_key:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(
                        ALPHAVANTAGE_URL,
                        params={
                            "function": "INSIDER_TRANSACTIONS",
                            "symbol": symbol_upper,
                            "apikey": settings.alphavantage_api_key,
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                transactions = []
                for row in payload.get("data", [])[:limit]:
                    transactions.append(
                        {
                            "insider_name": str(row.get("name") or row.get("insider_name") or ""),
                            "relation": str(row.get("relation") or ""),
                            "transaction_type": str(row.get("transaction_type") or row.get("transactionCode") or ""),
                            "shares": float(row.get("shares") or row.get("share") or 0),
                            "share_price": float(row.get("share_price") or row.get("price") or 0),
                            "value": float(row.get("value") or 0),
                            "filing_date": str(row.get("filing_date") or row.get("transaction_date") or ""),
                            "source": "alphavantage",
                        }
                    )
                return {
                    "symbol": symbol_upper,
                    "source": "alphavantage",
                    "transactions": transactions,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }
            except Exception as exc:
                logger.warning("Alpha Vantage insider activity unavailable for %s: %s", symbol_upper, exc)

        filings = await get_company_filings(symbol_upper, limit=limit * 2)
        fallback = [
            {
                "insider_name": "",
                "relation": "",
                "transaction_type": "Form 4 filed",
                "shares": 0.0,
                "share_price": 0.0,
                "value": 0.0,
                "filing_date": filing.get("filed_at", ""),
                "source": "sec",
                "url": filing.get("url", ""),
            }
            for filing in filings.get("filings", [])
            if filing.get("form") == "4"
        ][:limit]

        return {
            "symbol": symbol_upper,
            "source": "sec",
            "transactions": fallback,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    return await get_or_fetch(f"insider:{symbol_upper}", _fetch, INSIDER_TTL) or {
        "symbol": symbol_upper,
        "source": "unknown",
        "transactions": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

