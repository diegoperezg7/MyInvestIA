"""News aggregation and AI analysis backed by the provider layer."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from app.services.ai_service import ai_service
from app.services.cache import get_or_fetch
from app.services.data_providers import news_provider_aggregator
from app.services.news_intelligence import (
    build_source_health,
    cluster_narratives,
    deduplicate_articles,
    score_article,
)

logger = logging.getLogger(__name__)

FEED_TTL = 300
_article_store: dict[str, dict] = {}


async def get_aggregated_news(limit: int = 40) -> list[dict]:
    async def _fetch():
        articles = await news_provider_aggregator.fetch(limit=max(limit * 2, 40))
        normalized: list[dict] = []
        for article in articles:
            item = dict(article)
            item.setdefault("id", str(uuid.uuid4()))
            normalized.append(item)
        normalized.sort(key=lambda article: article.get("datetime", 0), reverse=True)
        return normalized

    return await get_or_fetch("news:aggregated", _fetch, FEED_TTL) or []


def _count_categories(articles: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {"news": 0, "social": 0, "blog": 0}
    for article in articles:
        category = article.get("source_category", "news")
        counts[category] = counts.get(category, 0) + 1
    return counts


async def get_ai_analyzed_feed(limit: int = 30) -> dict:
    async def _fetch():
        articles = await get_aggregated_news(limit=limit)
        if not articles:
            return {
                "articles": [],
                "sources_active": _get_sources_status(),
                "category_counts": {"news": 0, "social": 0, "blog": 0},
                "top_narratives": [],
                "source_health": {},
            }

        analyzed = await _batch_analyze(articles)
        enriched = [score_article(article) for article in analyzed]
        deduped = deduplicate_articles(enriched)[:limit]
        top_narratives = cluster_narratives(deduped, limit=5)
        source_health = build_source_health(deduped, _get_sources_status())

        for article in deduped:
            _article_store[article["id"]] = article

        return {
            "articles": deduped,
            "sources_active": _get_sources_status(),
            "category_counts": _count_categories(deduped),
            "top_narratives": top_narratives,
            "source_health": source_health,
        }

    return await get_or_fetch("news:ai_feed", _fetch, FEED_TTL) or {
        "articles": [],
        "sources_active": _get_sources_status(),
        "category_counts": {"news": 0, "social": 0, "blog": 0},
        "top_narratives": [],
        "source_health": {},
    }


async def get_article_analysis(article_id: str) -> dict | None:
    return _article_store.get(article_id)


async def _batch_analyze(articles: list[dict]) -> list[dict]:
    if not ai_service.is_configured or not articles:
        return [{**article, "ai_analysis": None} for article in articles]

    analyzed: list[dict] = []
    batch_size = 8

    for index in range(0, len(articles), batch_size):
        batch = articles[index : index + batch_size]
        try:
            results = await _analyze_batch(batch)
            for article, analysis in zip(batch, results):
                article["ai_analysis"] = analysis
                analyzed.append(article)
        except Exception as exc:
            logger.warning("Batch analysis failed: %s", exc)
            for article in batch:
                article["ai_analysis"] = None
                analyzed.append(article)

    return analyzed


async def _analyze_batch(articles: list[dict]) -> list[dict]:
    headlines = []
    for index, article in enumerate(articles):
        headlines.append(f"{index + 1}. [{article.get('source', '')}] {article['headline']}")
        if article.get("summary"):
            headlines.append(f"   Summary: {article['summary'][:200]}")

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
            model="llama3.1-8b",
            max_tokens=1500,
            system_override=(
                "You are a financial news analyst. Analyze articles for market impact. "
                "Respond with ONLY valid JSON. No markdown code blocks."
            ),
        )

        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        analyses = json.loads(text)
        if isinstance(analyses, list):
            while len(analyses) < len(articles):
                analyses.append(None)
            return [
                _validate_analysis(analysis) if analysis else None
                for analysis in analyses[: len(articles)]
            ]
    except (json.JSONDecodeError, Exception) as exc:
        logger.warning("AI batch analysis parse failed: %s", exc)

    return [None] * len(articles)


def _validate_analysis(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    try:
        return {
            "impact_score": max(1, min(10, int(raw.get("impact_score", 5)))),
            "affected_tickers": [
                str(ticker).upper()
                for ticker in raw.get("affected_tickers", [])
                if isinstance(ticker, str)
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
    return news_provider_aggregator.source_status()
