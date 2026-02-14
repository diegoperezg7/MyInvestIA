"""News aggregator: combines Finnhub + NewsAPI + RSS + Reddit + StockTwits + Twitter with AI analysis.

Merges articles from all sources, deduplicates by headline similarity,
and batch-analyzes with Mistral for impact scoring.
"""

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone

from app.services.ai_service import ai_service
from app.services.cache import get_or_fetch
from app.services.news_service import news_service
from app.services.newsapi_service import newsapi_service
from app.services.rss_service import get_rss_news
from app.services.reddit_service import get_reddit_posts
from app.services.stocktwits_service import get_trending as get_stocktwits_trending
from app.services.twitter_service import get_twitter_posts

logger = logging.getLogger(__name__)

FEED_TTL = 300  # 5 minutes

# Store analyzed articles in memory for individual lookup
_article_store: dict[str, dict] = {}


def _headline_key(headline: str) -> str:
    """Generate a dedup key from a headline (lowercase, stripped)."""
    normalized = headline.lower().strip()
    # Remove common prefixes/suffixes
    for prefix in ("breaking:", "update:", "exclusive:"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()
    return hashlib.md5(normalized.encode()).hexdigest()[:12]


# Default source_category by provider
_PROVIDER_CATEGORY: dict[str, str] = {
    "finnhub": "news",
    "newsapi": "news",
    "rss": "news",       # overridden per-article from RSS feed config
    "reddit": "social",
    "stocktwits": "social",
    "twitter": "social",
}


async def get_aggregated_news(limit: int = 40) -> list[dict]:
    """Fetch from all sources in parallel, merge, deduplicate, sort by time."""

    async def _fetch():
        tasks: dict[str, asyncio.Task] = {}
        async with asyncio.TaskGroup() as tg:
            tasks["finnhub"] = tg.create_task(news_service.get_market_news(limit=15))
            tasks["newsapi"] = tg.create_task(newsapi_service.get_business_news(limit=15))
            tasks["rss"] = tg.create_task(get_rss_news(limit=20))
            tasks["reddit"] = tg.create_task(get_reddit_posts(limit=15))
            tasks["stocktwits"] = tg.create_task(get_stocktwits_trending(limit=15))
            tasks["twitter"] = tg.create_task(get_twitter_posts(limit=10))

        # Tag each article with source_provider and source_category
        all_articles: list[dict] = []
        seen_keys: set[str] = set()

        for provider, task in tasks.items():
            try:
                articles = task.result()
                for article in articles:
                    key = _headline_key(article.get("headline", ""))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        article["source_provider"] = provider
                        article["id"] = str(uuid.uuid4())
                        # Use article-level category if set (RSS propagates it),
                        # otherwise fall back to provider default
                        if "source_category" not in article:
                            article["source_category"] = _PROVIDER_CATEGORY.get(provider, "news")
                        all_articles.append(article)
            except Exception as e:
                logger.warning("News source %s failed: %s", provider, e)

        # Sort by datetime descending
        all_articles.sort(key=lambda a: a.get("datetime", 0), reverse=True)
        return all_articles[:limit]

    return await get_or_fetch("news:aggregated", _fetch, FEED_TTL) or []


def _count_categories(articles: list[dict]) -> dict[str, int]:
    """Count articles by source_category."""
    counts: dict[str, int] = {"news": 0, "social": 0, "blog": 0}
    for a in articles:
        cat = a.get("source_category", "news")
        counts[cat] = counts.get(cat, 0) + 1
    return counts


async def get_ai_analyzed_feed(limit: int = 30) -> dict:
    """Get news feed with AI analysis for each article."""

    async def _fetch():
        articles = await get_aggregated_news(limit=limit)
        if not articles:
            return {
                "articles": [],
                "sources_active": _get_sources_status(),
                "category_counts": {"news": 0, "social": 0, "blog": 0},
            }

        # Batch AI analysis
        analyzed = await _batch_analyze(articles)

        # Store articles for individual lookup
        for article in analyzed:
            _article_store[article["id"]] = article

        return {
            "articles": analyzed,
            "sources_active": _get_sources_status(),
            "category_counts": _count_categories(analyzed),
        }

    return await get_or_fetch("news:ai_feed", _fetch, FEED_TTL) or {
        "articles": [],
        "sources_active": _get_sources_status(),
        "category_counts": {"news": 0, "social": 0, "blog": 0},
    }


async def get_article_analysis(article_id: str) -> dict | None:
    """Get detailed analysis for a specific article."""
    return _article_store.get(article_id)


async def _batch_analyze(articles: list[dict]) -> list[dict]:
    """Batch analyze articles using AI in groups of 5-10."""
    if not ai_service.is_configured or not articles:
        # Return articles without AI analysis
        return [
            {**a, "ai_analysis": None}
            for a in articles
        ]

    analyzed: list[dict] = []
    batch_size = 8

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        try:
            results = await _analyze_batch(batch)
            for article, analysis in zip(batch, results):
                article["ai_analysis"] = analysis
                analyzed.append(article)
        except Exception as e:
            logger.warning("Batch analysis failed: %s", e)
            for article in batch:
                article["ai_analysis"] = None
                analyzed.append(article)

    return analyzed


async def _analyze_batch(articles: list[dict]) -> list[dict]:
    """Analyze a batch of articles with a single AI call."""
    headlines = []
    for i, a in enumerate(articles):
        headlines.append(f"{i+1}. [{a.get('source', '')}] {a['headline']}")
        if a.get("summary"):
            headlines.append(f"   Summary: {a['summary'][:200]}")

    prompt = (
        "Analyze these financial news articles and social media posts. For EACH item, provide a JSON analysis.\n"
        "Items may include traditional news, Reddit posts, StockTwits messages, or tweets — "
        "interpret informal language, memes, and slang in a financial context.\n\n"
        + "\n".join(headlines)
        + "\n\nRespond with ONLY a JSON array (no markdown, no explanation). Each item must have:\n"
        '{"impact_score": 1-10, "affected_tickers": ["SYM"], "sentiment": "positive"|"negative"|"neutral", '
        '"urgency": "breaking"|"high"|"normal", "brief_analysis": "one sentence"}\n\n'
        f"Return exactly {len(articles)} items in the array, one per article, in order."
    )

    try:
        response = await ai_service.chat(
            messages=[{"role": "user", "content": prompt}],
            model="mistral-small-latest",
            max_tokens=1500,
            system_override=(
                "You are a financial news analyst. Analyze articles for market impact. "
                "Respond with ONLY valid JSON. No markdown code blocks."
            ),
        )

        # Parse JSON response
        text = response.strip()
        # Remove markdown code blocks if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        analyses = json.loads(text)
        if isinstance(analyses, list):
            # Pad or trim to match articles count
            while len(analyses) < len(articles):
                analyses.append(None)
            return [
                _validate_analysis(a) if a else None
                for a in analyses[:len(articles)]
            ]
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("AI batch analysis parse failed: %s", e)

    return [None] * len(articles)


def _validate_analysis(raw: dict) -> dict | None:
    """Validate and normalize an AI analysis result."""
    if not isinstance(raw, dict):
        return None
    try:
        return {
            "impact_score": max(1, min(10, int(raw.get("impact_score", 5)))),
            "affected_tickers": [
                str(t).upper() for t in raw.get("affected_tickers", [])
                if isinstance(t, str)
            ][:10],
            "sentiment": raw.get("sentiment", "neutral")
            if raw.get("sentiment") in ("positive", "negative", "neutral")
            else "neutral",
            "urgency": raw.get("urgency", "normal")
            if raw.get("urgency") in ("breaking", "high", "normal")
            else "normal",
            "brief_analysis": str(raw.get("brief_analysis", ""))[:300],
        }
    except Exception:
        return None


def _get_sources_status() -> dict[str, bool]:
    """Return which news sources are active."""
    return {
        "finnhub": news_service.is_configured,
        "newsapi": newsapi_service.is_configured,
        "rss": True,       # RSS is always available
        "reddit": True,    # Public JSON API, no key needed
        "stocktwits": True, # Public API, no key needed
        "twitter": True,   # Best-effort via Nitter
    }
