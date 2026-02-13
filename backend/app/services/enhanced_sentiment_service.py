"""Enhanced sentiment service combining multiple data sources.

Unifies AI sentiment, social media (Finnhub), NewsAPI, and RSS mentions
into a single weighted sentiment score.
"""

import asyncio
import logging
from datetime import datetime, timezone

from app.services.cache import get_or_fetch
from app.services.news_service import news_service
from app.services.newsapi_service import newsapi_service
from app.services.rss_service import get_rss_news
from app.services.sentiment_service import analyze_sentiment

logger = logging.getLogger(__name__)

ENHANCED_TTL = 300  # 5 minutes

# Source weights for unified score
WEIGHTS = {
    "ai_sentiment": 0.40,
    "social": 0.30,
    "news": 0.30,
}


async def get_enhanced_sentiment(symbol: str) -> dict:
    """Get multi-source sentiment analysis for a symbol."""
    symbol = symbol.upper()

    async def _fetch():
        sources: list[dict] = []
        total_data_points = 0

        # Parallel fetch of all sources
        tasks: dict[str, asyncio.Task] = {}
        async with asyncio.TaskGroup() as tg:
            tasks["ai"] = tg.create_task(
                _get_ai_sentiment(symbol)
            )
            tasks["social"] = tg.create_task(
                news_service.get_social_sentiment(symbol)
            )
            tasks["newsapi"] = tg.create_task(
                newsapi_service.get_symbol_news(symbol, limit=10)
            )
            tasks["rss"] = tg.create_task(
                get_rss_news(limit=30)
            )

        # 1. AI Sentiment (weight: 40%)
        ai_result = tasks["ai"].result()
        ai_score = 0.0
        if ai_result:
            ai_score = ai_result.get("score", 0.0)
            total_data_points += ai_result.get("sources_count", 1)
            sources.append({
                "source_name": "AI Sentiment",
                "score": ai_score,
                "weight": WEIGHTS["ai_sentiment"],
                "details": {
                    "label": ai_result.get("label", "neutral"),
                    "narrative": ai_result.get("narrative", "")[:200],
                    "sources_count": ai_result.get("sources_count", 0),
                },
            })

        # 2. Social Sentiment (weight: 30%)
        social_result = tasks["social"].result()
        social_score = 0.0
        if social_result:
            social_score = social_result.get("combined_score", 0.0)
            total_data_points += social_result.get("total_mentions", 0)
            sources.append({
                "source_name": "Social Media (Reddit + Twitter)",
                "score": social_score,
                "weight": WEIGHTS["social"],
                "details": {
                    "total_mentions": social_result.get("total_mentions", 0),
                    "reddit_mentions": social_result.get("reddit", {}).get("mentions", 0),
                    "twitter_mentions": social_result.get("twitter", {}).get("mentions", 0),
                    "buzz_level": social_result.get("buzz_level", "none"),
                },
            })

        # 3. News Sentiment (weight: 30%) — from NewsAPI + RSS keyword match
        newsapi_articles = tasks["newsapi"].result()
        rss_articles = tasks["rss"].result()

        # Count RSS mentions of the symbol
        rss_mentions = [
            a for a in rss_articles
            if symbol.lower() in (a.get("headline", "") + " " + a.get("summary", "")).lower()
        ]

        news_count = len(newsapi_articles) + len(rss_mentions)
        total_data_points += news_count

        # Simple heuristic: more news = more attention, headline sentiment is hard to parse
        # without AI, so we use a neutral base shifted by article count
        news_score = 0.0
        if news_count > 0:
            # Having news coverage is slightly positive (attention = interest)
            news_score = min(0.3, news_count * 0.05)

        sources.append({
            "source_name": "News Coverage",
            "score": news_score,
            "weight": WEIGHTS["news"],
            "details": {
                "newsapi_articles": len(newsapi_articles),
                "rss_mentions": len(rss_mentions),
                "total_articles": news_count,
            },
        })

        # Compute unified score
        unified_score = 0.0
        total_weight = 0.0
        for src in sources:
            unified_score += src["score"] * src["weight"]
            total_weight += src["weight"]

        if total_weight > 0:
            unified_score = unified_score / total_weight

        # Clamp to [-1, 1]
        unified_score = max(-1.0, min(1.0, unified_score))

        # Label
        if unified_score >= 0.2:
            label = "bullish"
        elif unified_score <= -0.2:
            label = "bearish"
        else:
            label = "neutral"

        return {
            "symbol": symbol,
            "unified_score": round(unified_score, 4),
            "unified_label": label,
            "sources": sources,
            "total_data_points": total_data_points,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    return await get_or_fetch(f"enhanced_sentiment:{symbol}", _fetch, ENHANCED_TTL) or {
        "symbol": symbol,
        "unified_score": 0.0,
        "unified_label": "neutral",
        "sources": [],
        "total_data_points": 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def _get_ai_sentiment(symbol: str) -> dict | None:
    """Get AI sentiment, returning None on failure."""
    try:
        from app.services.market_data import market_data_service
        from app.services.technical_analysis import compute_all_indicators

        quote = await market_data_service.get_quote(symbol)
        history = await market_data_service.get_history(symbol, period="6mo", interval="1d")

        technical_data = None
        if history and len(history) >= 30:
            closes = [r["close"] for r in history]
            technical_data = compute_all_indicators(closes)

        return await analyze_sentiment(
            symbol=symbol,
            asset_type="stock",
            quote_data=dict(quote) if quote else None,
            technical_data=technical_data,
        )
    except Exception as e:
        logger.warning("AI sentiment for %s failed: %s", symbol, e)
        return None
