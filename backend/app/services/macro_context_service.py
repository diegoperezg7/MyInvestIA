"""Official/public macro context from FRED, World Bank, and Alternative.me."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.services.cache import get_or_fetch

logger = logging.getLogger(__name__)

MACRO_CONTEXT_TTL = 1800
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
WORLD_BANK_URL = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
ALT_FEAR_GREED_URL = "https://api.alternative.me/fng/"

FRED_SERIES = {
    "FEDFUNDS": {"name": "Fed Funds Rate", "unit": "%", "source": "fred"},
    "UNRATE": {"name": "US Unemployment Rate", "unit": "%", "source": "fred"},
    "CPIAUCSL": {"name": "US CPI Index", "unit": "index", "source": "fred"},
}

WORLD_BANK_SERIES = {
    "NY.GDP.MKTP.KD.ZG": {"name": "Real GDP Growth", "unit": "%", "source": "worldbank"},
    "FP.CPI.TOTL.ZG": {"name": "Inflation, consumer prices", "unit": "%", "source": "worldbank"},
}


def _safe_float(value: object) -> float | None:
    try:
        if value in ("", None, "."):
            return None
        return float(value)
    except Exception:
        return None


async def _fetch_fred_series(client: httpx.AsyncClient, series_id: str) -> dict | None:
    if not settings.fred_api_key:
        return None
    response = await client.get(
        FRED_URL,
        params={
            "series_id": series_id,
            "api_key": settings.fred_api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 2,
        },
    )
    response.raise_for_status()
    observations = response.json().get("observations", [])
    values = [item for item in observations if _safe_float(item.get("value")) is not None]
    if not values:
        return None
    current = _safe_float(values[0]["value"])
    previous = _safe_float(values[1]["value"]) if len(values) > 1 else current
    if current is None:
        return None
    change_pct = 0.0
    if previous not in (None, 0):
        change_pct = ((current - previous) / abs(previous)) * 100
    meta = FRED_SERIES[series_id]
    return {
        "id": series_id,
        "name": meta["name"],
        "value": round(current, 4),
        "date": str(values[0].get("date") or ""),
        "change_percent": round(change_pct, 4),
        "unit": meta["unit"],
        "source": meta["source"],
    }


async def _fetch_world_bank_series(client: httpx.AsyncClient, indicator: str) -> dict | None:
    response = await client.get(
        WORLD_BANK_URL.format(country=settings.worldbank_country, indicator=indicator),
        params={"format": "json", "per_page": 4},
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or len(payload) < 2:
        return None
    records = payload[1]
    values = [record for record in records if _safe_float(record.get("value")) is not None]
    if not values:
        return None
    current = _safe_float(values[0]["value"])
    previous = _safe_float(values[1]["value"]) if len(values) > 1 else current
    if current is None:
        return None
    change_pct = 0.0
    if previous not in (None, 0):
        change_pct = ((current - previous) / abs(previous)) * 100
    meta = WORLD_BANK_SERIES[indicator]
    return {
        "id": indicator,
        "name": meta["name"],
        "value": round(current, 4),
        "date": str(values[0].get("date") or ""),
        "change_percent": round(change_pct, 4),
        "unit": meta["unit"],
        "source": meta["source"],
    }


async def _fetch_fear_greed(client: httpx.AsyncClient) -> dict | None:
    response = await client.get(ALT_FEAR_GREED_URL, params={"limit": 1})
    response.raise_for_status()
    payload = response.json().get("data", [])
    if not payload:
        return None
    item = payload[0]
    timestamp = str(item.get("timestamp") or "")
    if timestamp.isdigit():
        timestamp = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()
    return {
        "value": int(item.get("value") or 0),
        "classification": str(item.get("value_classification") or "unknown"),
        "timestamp": timestamp,
        "source": "alternative.me",
    }


async def get_macro_context() -> dict:
    async def _fetch():
        async with httpx.AsyncClient(timeout=15.0) as client:
            official_series = []
            sources = [
                {
                    "name": "fred",
                    "active": bool(settings.fred_api_key),
                    "retrieval_mode": "official_api",
                    "confidence": 0.95 if settings.fred_api_key else 0.0,
                    "note": "Federal Reserve Economic Data",
                },
                {
                    "name": "worldbank",
                    "active": True,
                    "retrieval_mode": "official_api",
                    "confidence": 0.90,
                    "note": f"World Bank country scope: {settings.worldbank_country}",
                },
                {
                    "name": "alternative_me",
                    "active": True,
                    "retrieval_mode": "public_api",
                    "confidence": 0.75,
                    "note": "Crypto fear & greed index",
                },
                {
                    "name": "bls",
                    "active": bool(settings.bls_api_key),
                    "retrieval_mode": "official_api",
                    "confidence": 0.85 if settings.bls_api_key else 0.0,
                    "note": "Reserved for future labor/inflation series",
                },
            ]

            for series_id in FRED_SERIES:
                try:
                    result = await _fetch_fred_series(client, series_id)
                    if result:
                        official_series.append(result)
                except Exception as exc:
                    logger.debug("FRED series %s unavailable: %s", series_id, exc)

            for indicator in WORLD_BANK_SERIES:
                try:
                    result = await _fetch_world_bank_series(client, indicator)
                    if result:
                        official_series.append(result)
                except Exception as exc:
                    logger.debug("World Bank series %s unavailable: %s", indicator, exc)

            fear_greed = None
            try:
                fear_greed = await _fetch_fear_greed(client)
            except Exception as exc:
                logger.debug("Fear & Greed unavailable: %s", exc)

            return {
                "official_series": official_series,
                "sources": sources,
                "fear_greed": fear_greed,
            }

    return await get_or_fetch("macro:context", _fetch, MACRO_CONTEXT_TTL) or {
        "official_series": [],
        "sources": [],
        "fear_greed": None,
    }

