"""GDELT news feed integration for broad free news coverage."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from app.services.cache import get_or_fetch

logger = logging.getLogger(__name__)

GDELT_TTL = 300
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def _parse_datetime(value: str) -> int:
    if not value:
        return 0
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return int(parsed.astimezone(timezone.utc).timestamp())
    except Exception:
        return 0


async def get_gdelt_news(limit: int = 15) -> list[dict]:
    async def _fetch():
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(
                    GDELT_URL,
                    params={
                        "query": "(finance OR markets OR stocks OR crypto)",
                        "mode": "ArtList",
                        "maxrecords": limit,
                        "format": "json",
                        "sort": "HybridRel",
                        "timespan": "1day",
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            logger.debug("GDELT news unavailable: %s", exc)
            return []

        articles = []
        for item in payload.get("articles", [])[:limit]:
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            articles.append(
                {
                    "headline": title,
                    "summary": str(item.get("seendate") or ""),
                    "source": str(item.get("sourceCommonName") or "GDELT"),
                    "url": str(item.get("url") or ""),
                    "datetime": _parse_datetime(str(item.get("seendate") or "")),
                    "source_category": "news",
                }
            )
        return articles

    return await get_or_fetch("gdelt:news", _fetch, GDELT_TTL) or []

