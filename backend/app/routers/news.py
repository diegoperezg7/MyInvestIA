"""News feed router — AI-analyzed multi-source news."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user
from app.services.news_aggregator import get_ai_analyzed_feed, get_article_analysis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/news", tags=["news"], dependencies=[Depends(get_current_user)])


@router.get("/feed")
async def get_news_feed():
    """Get AI-analyzed news feed from all sources (Finnhub + NewsAPI + RSS + Reddit + StockTwits + Twitter)."""
    try:
        result = await get_ai_analyzed_feed(limit=30)
        return {
            "articles": result.get("articles", []),
            "total": len(result.get("articles", [])),
            "sources_active": result.get("sources_active", {}),
            "category_counts": result.get("category_counts", {"news": 0, "social": 0, "blog": 0}),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("News feed error: %s", e)
        raise HTTPException(status_code=500, detail=f"News feed error: {e}")


@router.get("/article/{article_id}")
async def get_article(article_id: str):
    """Get detailed analysis for a specific article."""
    article = await get_article_analysis(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article
