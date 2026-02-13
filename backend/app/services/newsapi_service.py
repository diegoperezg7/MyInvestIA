"""NewsAPI.org integration for financial news.

Free tier: 100 requests/day. Caches aggressively to conserve quota.
"""

import logging
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.services.cache import get_or_fetch

logger = logging.getLogger(__name__)

NEWSAPI_BASE = "https://newsapi.org/v2"
NEWSAPI_TTL = 600  # 10 minutes — conserve rate limit

# In-memory daily counter
_daily_counter = {"date": "", "count": 0}


def _track_request():
    """Track daily API usage."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _daily_counter["date"] != today:
        _daily_counter["date"] = today
        _daily_counter["count"] = 0
    _daily_counter["count"] += 1


def get_daily_usage() -> dict:
    """Return current daily usage stats."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _daily_counter["date"] != today:
        return {"date": today, "count": 0, "limit": 100}
    return {"date": today, "count": _daily_counter["count"], "limit": 100}


class NewsAPIService:
    """Fetches news from NewsAPI.org."""

    @property
    def is_configured(self) -> bool:
        return bool(settings.newsapi_key)

    async def get_business_news(self, limit: int = 15) -> list[dict]:
        """Fetch general business/finance news headlines."""
        if not self.is_configured:
            return []

        async def _fetch():
            try:
                _track_request()
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"{NEWSAPI_BASE}/top-headlines",
                        params={
                            "category": "business",
                            "language": "en",
                            "pageSize": limit,
                            "apiKey": settings.newsapi_key,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

                articles = []
                for a in data.get("articles", []):
                    title = a.get("title", "")
                    if not title or title == "[Removed]":
                        continue
                    articles.append({
                        "headline": title,
                        "summary": a.get("description", "") or "",
                        "source": a.get("source", {}).get("name", "NewsAPI"),
                        "url": a.get("url", ""),
                        "datetime": _parse_iso_timestamp(a.get("publishedAt", "")),
                    })
                return articles
            except Exception as e:
                logger.warning("NewsAPI business news failed: %s", e)
                return []

        return await get_or_fetch("newsapi:business", _fetch, NEWSAPI_TTL) or []

    async def get_symbol_news(self, symbol: str, limit: int = 5) -> list[dict]:
        """Fetch news mentioning a specific company/ticker."""
        if not self.is_configured:
            return []

        symbol = symbol.upper()

        async def _fetch():
            try:
                _track_request()
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"{NEWSAPI_BASE}/everything",
                        params={
                            "q": symbol,
                            "language": "en",
                            "sortBy": "publishedAt",
                            "pageSize": limit,
                            "apiKey": settings.newsapi_key,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

                articles = []
                for a in data.get("articles", []):
                    title = a.get("title", "")
                    if not title or title == "[Removed]":
                        continue
                    articles.append({
                        "headline": title,
                        "summary": a.get("description", "") or "",
                        "source": a.get("source", {}).get("name", "NewsAPI"),
                        "url": a.get("url", ""),
                        "datetime": _parse_iso_timestamp(a.get("publishedAt", "")),
                        "related": symbol,
                    })
                return articles
            except Exception as e:
                logger.warning("NewsAPI symbol news for %s failed: %s", symbol, e)
                return []

        return await get_or_fetch(f"newsapi:symbol:{symbol}", _fetch, NEWSAPI_TTL) or []


def _parse_iso_timestamp(iso_str: str) -> int:
    """Parse ISO 8601 timestamp to unix epoch."""
    if not iso_str:
        return 0
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except Exception:
        return 0


# Singleton
newsapi_service = NewsAPIService()
