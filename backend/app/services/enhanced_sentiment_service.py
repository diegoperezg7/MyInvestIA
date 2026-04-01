"""Enhanced sentiment service backed by the structured sentiment engine."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.services.cache import get_or_fetch
from app.services.news_aggregator import get_ai_analyzed_feed
from app.services.news_intelligence import (
    build_social_sentiment_from_articles,
    resolve_ticker_mentions,
)
from app.services.news_service import news_service
from app.services.newsapi_service import newsapi_service
from app.services.rss_service import get_rss_news
from app.services.sentiment_engine import build_enhanced_sentiment
from app.services.sentiment_service import analyze_sentiment

logger = logging.getLogger(__name__)

ENHANCED_TTL = 300  # 5 minutes


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fallback_articles(symbol: str, newsapi_articles: list[dict], rss_articles: list[dict]) -> list[dict]:
    symbol_upper = symbol.upper()
    now_ts = int(datetime.now(timezone.utc).timestamp())
    fallback: list[dict] = []

    def append_article(article: dict, provider: str, index: int) -> None:
        headline = str(article.get("headline") or article.get("title") or "").strip()
        summary = str(article.get("summary") or article.get("description") or "").strip()
        if not headline:
            return
        payload = {
            "id": f"fallback-{provider}-{index}",
            "headline": headline,
            "summary": summary,
            "datetime": int(article.get("datetime") or now_ts),
            "source": str(article.get("source") or provider),
            "source_provider": provider,
            "source_category": "news",
            "url": article.get("url", ""),
            "related": article.get("related", symbol_upper),
        }
        mentions = resolve_ticker_mentions(payload)
        if symbol_upper not in set(mentions) and symbol_upper not in str(payload.get("related") or "").upper():
            return
        payload["ticker_mentions"] = mentions
        fallback.append(payload)

    for index, article in enumerate(newsapi_articles or []):
        append_article(article, "newsapi", index)
    for index, article in enumerate(rss_articles or []):
        append_article(article, "rss", index)
    return fallback


async def get_enhanced_sentiment(symbol: str) -> dict:
    """Get multi-source sentiment analysis for a symbol."""
    symbol_upper = symbol.upper()

    async def _fetch():
        results = await asyncio.gather(
            _get_ai_sentiment(symbol_upper),
            news_service.get_social_sentiment(symbol_upper),
            get_ai_analyzed_feed(limit=60),
            newsapi_service.get_symbol_news(symbol_upper, limit=8),
            get_rss_news(limit=20),
            return_exceptions=True,
        )

        ai_result = results[0] if isinstance(results[0], dict) else None
        raw_social = results[1] if isinstance(results[1], dict) else None
        feed_result = results[2] if isinstance(results[2], dict) else {}
        newsapi_articles = results[3] if isinstance(results[3], list) else []
        rss_articles = results[4] if isinstance(results[4], list) else []

        analyzed_articles = feed_result.get("articles", [])
        symbol_articles = [
            article
            for article in analyzed_articles
            if symbol_upper in set(article.get("ticker_mentions") or [])
        ]
        fallback_articles = _fallback_articles(symbol_upper, newsapi_articles, rss_articles)
        merged_articles = symbol_articles + fallback_articles

        social_result = raw_social or build_social_sentiment_from_articles(symbol_upper, merged_articles)
        return build_enhanced_sentiment(
            symbol_upper,
            merged_articles,
            ai_sentiment=ai_result,
            social_snapshot=social_result,
            source_health=feed_result.get("source_health", {}),
        )

    return await get_or_fetch(f"enhanced_sentiment:{symbol_upper}", _fetch, ENHANCED_TTL) or {
        "symbol": symbol_upper,
        "unified_score": 0.0,
        "unified_label": "neutral",
        "sources": [],
        "divergences": [],
        "coverage_confidence": 0.0,
        "news_momentum": 0.0,
        "social_momentum": 0.0,
        "recent_shift": 0.0,
        "signal_to_noise": 0.0,
        "noise_ratio": 0.0,
        "temporal_aggregation": {"1h": {}, "24h": {}, "7d": {}},
        "items": [],
        "top_narratives": [],
        "source_breakdown": [],
        "cross_source_divergence": 0.0,
        "source_health": {},
        "total_data_points": 0,
        "warnings": ["Sentiment snapshot unavailable."],
        "classifier": {"provider": "heuristic", "available": False},
        "generated_at": _iso_now(),
    }


async def _get_ai_sentiment(symbol: str) -> dict | None:
    """Get AI narrative sentiment, returning None on failure."""
    try:
        from app.services.market_data import market_data_service
        from app.services.technical_analysis import compute_all_indicators

        quote = await market_data_service.get_quote(symbol)
        history = await market_data_service.get_history(symbol, period="6mo", interval="1d")

        technical_data = None
        if history and len(history) >= 30:
            closes = [r["close"] for r in history]
            technical_data = compute_all_indicators(closes)

        social_data = None
        try:
            social_data = await news_service.get_social_sentiment(symbol)
        except Exception:
            social_data = None

        return await analyze_sentiment(
            symbol=symbol,
            asset_type="stock",
            quote_data=dict(quote) if quote else None,
            technical_data=technical_data,
            social_data=social_data,
        )
    except Exception as exc:
        logger.warning("AI sentiment for %s failed: %s", symbol, exc)
        return None
