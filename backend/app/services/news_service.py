"""Finnhub news & social sentiment service.

Uses the Finnhub free tier (60 calls/min) to fetch:
- General market news headlines
- Company-specific news for portfolio/watchlist symbols
- Social sentiment (Reddit + Twitter) buzz and scores per symbol
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings
from app.services.cache import get_or_fetch

logger = logging.getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1"
NEWS_TTL = 300  # 5 minutes


class NewsService:
    """Fetches news from Finnhub API."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    @property
    def is_configured(self) -> bool:
        return bool(settings.finnhub_api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_market_news(self, limit: int = 10) -> list[dict]:
        """Fetch general market news headlines."""
        if not self.is_configured:
            return []

        async def _fetch():
            try:
                client = await self._get_client()
                resp = await client.get(
                    f"{FINNHUB_BASE}/news",
                    params={
                        "category": "general",
                        "token": settings.finnhub_api_key,
                    },
                )
                resp.raise_for_status()
                articles = resp.json()
                return [
                    {
                        "headline": a.get("headline", ""),
                        "summary": a.get("summary", ""),
                        "source": a.get("source", ""),
                        "url": a.get("url", ""),
                        "datetime": a.get("datetime", 0),
                        "related": a.get("related", ""),
                    }
                    for a in articles[:limit]
                    if a.get("headline")
                ]
            except Exception as e:
                logger.warning("Failed to fetch market news: %s", e)
                return []

        return await get_or_fetch("news:market", _fetch, NEWS_TTL) or []

    async def get_company_news(
        self, symbol: str, days: int = 3, limit: int = 5
    ) -> list[dict]:
        """Fetch company-specific news for a symbol."""
        if not self.is_configured:
            return []

        symbol = symbol.upper()
        now = datetime.now(timezone.utc)
        date_from = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        date_to = now.strftime("%Y-%m-%d")

        async def _fetch():
            try:
                client = await self._get_client()
                resp = await client.get(
                    f"{FINNHUB_BASE}/company-news",
                    params={
                        "symbol": symbol,
                        "from": date_from,
                        "to": date_to,
                        "token": settings.finnhub_api_key,
                    },
                )
                resp.raise_for_status()
                articles = resp.json()
                return [
                    {
                        "headline": a.get("headline", ""),
                        "summary": a.get("summary", ""),
                        "source": a.get("source", ""),
                        "url": a.get("url", ""),
                        "datetime": a.get("datetime", 0),
                        "related": symbol,
                    }
                    for a in articles[:limit]
                    if a.get("headline")
                ]
            except Exception as e:
                logger.warning("Failed to fetch news for %s: %s", symbol, e)
                return []

        return await get_or_fetch(f"news:company:{symbol}", _fetch, NEWS_TTL) or []

    async def get_portfolio_news(
        self, symbols: list[str], limit_per_symbol: int = 3
    ) -> list[dict]:
        """Fetch news for multiple symbols in parallel, deduplicated."""
        if not self.is_configured or not symbols:
            return []

        # Cap at 10 symbols to respect rate limits
        symbols = symbols[:10]

        tasks = [
            self.get_company_news(sym, limit=limit_per_symbol) for sym in symbols
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten and deduplicate by headline
        seen: set[str] = set()
        all_news: list[dict] = []
        for result in results:
            if isinstance(result, list):
                for article in result:
                    headline = article["headline"]
                    if headline not in seen:
                        seen.add(headline)
                        all_news.append(article)

        # Sort by datetime descending (most recent first)
        all_news.sort(key=lambda a: a.get("datetime", 0), reverse=True)
        return all_news

    # --- Social Sentiment (Reddit + Twitter) ---

    async def get_social_sentiment(self, symbol: str) -> dict | None:
        """Fetch social sentiment (Reddit + Twitter) for a symbol from Finnhub."""
        if not self.is_configured:
            return None

        symbol = symbol.upper()

        async def _fetch():
            try:
                client = await self._get_client()
                now = datetime.now(timezone.utc)
                resp = await client.get(
                    f"{FINNHUB_BASE}/stock/social-sentiment",
                    params={
                        "symbol": symbol,
                        "from": (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S"),
                        "to": now.strftime("%Y-%m-%dT%H:%M:%S"),
                        "token": settings.finnhub_api_key,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                reddit_data = data.get("reddit", [])
                twitter_data = data.get("twitter", [])

                def _aggregate(entries: list[dict]) -> dict:
                    if not entries:
                        return {
                            "mentions": 0,
                            "positive_mentions": 0,
                            "negative_mentions": 0,
                            "positive_score": 0.0,
                            "negative_score": 0.0,
                            "score": 0.0,
                        }
                    total_mentions = sum(e.get("mention", 0) for e in entries)
                    total_positive = sum(e.get("positiveMention", 0) for e in entries)
                    total_negative = sum(e.get("negativeMention", 0) for e in entries)
                    # Weighted average scores
                    n = len(entries)
                    avg_pos_score = sum(e.get("positiveScore", 0) for e in entries) / n
                    avg_neg_score = sum(e.get("negativeScore", 0) for e in entries) / n
                    avg_score = sum(e.get("score", 0) for e in entries) / n
                    return {
                        "mentions": total_mentions,
                        "positive_mentions": total_positive,
                        "negative_mentions": total_negative,
                        "positive_score": round(avg_pos_score, 4),
                        "negative_score": round(avg_neg_score, 4),
                        "score": round(avg_score, 4),
                    }

                reddit = _aggregate(reddit_data)
                twitter = _aggregate(twitter_data)

                total_mentions = reddit["mentions"] + twitter["mentions"]
                combined_score = 0.0
                if total_mentions > 0:
                    # Weight by mention count
                    combined_score = (
                        reddit["score"] * reddit["mentions"]
                        + twitter["score"] * twitter["mentions"]
                    ) / total_mentions

                # Classify buzz level
                if total_mentions >= 100:
                    buzz = "viral"
                elif total_mentions >= 30:
                    buzz = "high"
                elif total_mentions >= 10:
                    buzz = "moderate"
                elif total_mentions >= 1:
                    buzz = "low"
                else:
                    buzz = "none"

                # Classify sentiment
                if combined_score >= 0.3:
                    label = "bullish"
                elif combined_score <= -0.3:
                    label = "bearish"
                else:
                    label = "neutral"

                return {
                    "symbol": symbol,
                    "reddit": reddit,
                    "twitter": twitter,
                    "total_mentions": total_mentions,
                    "combined_score": round(combined_score, 4),
                    "buzz_level": buzz,
                    "sentiment_label": label,
                }
            except Exception as e:
                logger.warning("Social sentiment failed for %s: %s", symbol, e)
                return None

        return await get_or_fetch(f"social:{symbol}", _fetch, NEWS_TTL)

    async def get_portfolio_social_sentiment(
        self, symbols: list[str]
    ) -> list[dict]:
        """Fetch social sentiment for multiple symbols in parallel."""
        if not self.is_configured or not symbols:
            return []

        # Cap at 10 symbols to respect rate limits
        symbols = symbols[:10]

        tasks = [self.get_social_sentiment(sym) for sym in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, dict)]


# Singleton
news_service = NewsService()
