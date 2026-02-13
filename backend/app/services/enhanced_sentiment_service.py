"""Enhanced sentiment service combining multiple data sources.

Unifies AI sentiment, social media (Finnhub), NewsAPI, and RSS mentions
into a single weighted sentiment score. News headlines are analyzed by AI
instead of using a simple article-count heuristic.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from app.services.ai_service import ai_service, MODEL_SENTIMENT
from app.services.cache import get_or_fetch
from app.services.news_service import news_service
from app.services.newsapi_service import newsapi_service
from app.services.rss_service import get_rss_news
from app.services.sentiment_service import analyze_sentiment

logger = logging.getLogger(__name__)

ENHANCED_TTL = 300  # 5 minutes

# Source weights for unified score
WEIGHTS = {
    "ai_sentiment": 0.35,
    "social": 0.25,
    "news": 0.40,
}

NEWS_SENTIMENT_PROMPT = """Analyze the sentiment of these news headlines about {symbol}.

Headlines:
{headlines}

Return ONLY valid JSON:
{{
  "score": <float from -1.0 (very bearish) to 1.0 (very bullish)>,
  "label": "<bullish|bearish|neutral>",
  "positive_count": <int>,
  "negative_count": <int>,
  "neutral_count": <int>,
  "top_positive": "<most bullish headline or empty>",
  "top_negative": "<most bearish headline or empty>",
  "summary": "<1 sentence overall tone>"
}}

Consider:
- Earnings beats, upgrades, new products, partnerships → positive
- Lawsuits, downgrades, layoffs, misses, investigations → negative
- Routine coverage without clear direction → neutral
Be objective. If headlines are mixed, reflect that in a score near 0."""


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

        # 1. AI Sentiment (weight: 35%)
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
                    "strength": ai_result.get("strength", 3),
                    "divergences": ai_result.get("divergences", []),
                },
            })

        # 2. Social Sentiment (weight: 25%)
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

        # 3. News Sentiment (weight: 40%) — AI-analyzed headlines from NewsAPI + RSS
        newsapi_articles = tasks["newsapi"].result()
        rss_articles = tasks["rss"].result()

        # Filter RSS mentions of the symbol
        rss_mentions = [
            a for a in rss_articles
            if symbol.lower() in (a.get("headline", "") + " " + a.get("summary", "")).lower()
        ]

        # Collect all headlines for AI analysis
        all_headlines: list[str] = []
        for a in newsapi_articles:
            h = a.get("title") or a.get("headline", "")
            if h:
                all_headlines.append(h.strip())
        for a in rss_mentions:
            h = a.get("headline", "")
            if h:
                all_headlines.append(h.strip())

        news_count = len(all_headlines)
        total_data_points += news_count

        news_ai_result = await _analyze_news_headlines(symbol, all_headlines)
        news_score = news_ai_result.get("score", 0.0)

        sources.append({
            "source_name": "News Coverage (AI-Analyzed)",
            "score": news_score,
            "weight": WEIGHTS["news"],
            "details": {
                "newsapi_articles": len(newsapi_articles),
                "rss_mentions": len(rss_mentions),
                "total_articles": news_count,
                "positive_count": news_ai_result.get("positive_count", 0),
                "negative_count": news_ai_result.get("negative_count", 0),
                "neutral_count": news_ai_result.get("neutral_count", 0),
                "summary": news_ai_result.get("summary", ""),
                "top_positive": news_ai_result.get("top_positive", ""),
                "top_negative": news_ai_result.get("top_negative", ""),
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

        # Divergence detection
        divergences = _detect_divergences(sources, ai_score, social_score, news_score)

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
            "divergences": divergences,
            "total_data_points": total_data_points,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    return await get_or_fetch(f"enhanced_sentiment:{symbol}", _fetch, ENHANCED_TTL) or {
        "symbol": symbol,
        "unified_score": 0.0,
        "unified_label": "neutral",
        "sources": [],
        "divergences": [],
        "total_data_points": 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _detect_divergences(
    sources: list[dict], ai_score: float, social_score: float, news_score: float
) -> list[str]:
    """Flag when different sentiment sources significantly disagree."""
    divergences: list[str] = []
    threshold = 0.4

    if abs(ai_score - social_score) > threshold:
        ai_dir = "alcista" if ai_score > 0 else "bajista"
        social_dir = "alcista" if social_score > 0 else "bajista"
        divergences.append(
            f"IA técnica es {ai_dir} ({ai_score:+.2f}) pero redes sociales son {social_dir} ({social_score:+.2f})"
        )

    if abs(ai_score - news_score) > threshold:
        ai_dir = "alcista" if ai_score > 0 else "bajista"
        news_dir = "alcista" if news_score > 0 else "bajista"
        divergences.append(
            f"IA técnica es {ai_dir} ({ai_score:+.2f}) pero noticias son {news_dir} ({news_score:+.2f})"
        )

    if abs(social_score - news_score) > threshold:
        social_dir = "alcista" if social_score > 0 else "bajista"
        news_dir = "alcista" if news_score > 0 else "bajista"
        divergences.append(
            f"Redes sociales son {social_dir} ({social_score:+.2f}) pero noticias son {news_dir} ({news_score:+.2f})"
        )

    return divergences


async def _analyze_news_headlines(symbol: str, headlines: list[str]) -> dict:
    """Use AI to analyze news headline sentiment instead of heuristic counting."""
    if not headlines:
        return {"score": 0.0, "label": "neutral", "positive_count": 0,
                "negative_count": 0, "neutral_count": 0, "summary": "No news available."}

    if not ai_service.is_configured:
        # Fallback: mild positive for having coverage
        return {"score": min(0.15, len(headlines) * 0.03), "label": "neutral",
                "positive_count": 0, "negative_count": 0, "neutral_count": len(headlines),
                "summary": "AI unavailable — using basic coverage heuristic."}

    # Limit to 20 headlines to keep prompt concise
    trimmed = headlines[:20]
    headlines_text = "\n".join(f"- {h}" for h in trimmed)

    prompt = NEWS_SENTIMENT_PROMPT.format(symbol=symbol, headlines=headlines_text)

    try:
        response = await ai_service.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            model=MODEL_SENTIMENT,
        )
        return _parse_news_sentiment(response)
    except Exception as e:
        logger.warning("AI news sentiment for %s failed: %s", symbol, e)
        return {"score": 0.0, "label": "neutral", "positive_count": 0,
                "negative_count": 0, "neutral_count": len(headlines),
                "summary": "Analysis failed."}


def _parse_news_sentiment(text: str) -> dict:
    """Parse AI JSON response for news headline sentiment."""
    try:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            json_lines = []
            in_json = False
            for line in lines:
                if line.strip().startswith("```") and not in_json:
                    in_json = True
                    continue
                elif line.strip() == "```":
                    break
                elif in_json:
                    json_lines.append(line)
            cleaned = "\n".join(json_lines)

        data = json.loads(cleaned)
        score = max(-1.0, min(1.0, float(data.get("score", 0.0))))
        return {
            "score": round(score, 2),
            "label": data.get("label", "neutral"),
            "positive_count": int(data.get("positive_count", 0)),
            "negative_count": int(data.get("negative_count", 0)),
            "neutral_count": int(data.get("neutral_count", 0)),
            "top_positive": str(data.get("top_positive", "")),
            "top_negative": str(data.get("top_negative", "")),
            "summary": str(data.get("summary", "")),
        }
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse news sentiment: %s", e)
        return {"score": 0.0, "label": "neutral", "positive_count": 0,
                "negative_count": 0, "neutral_count": 0, "summary": "Parse error."}


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

        # Also fetch social data to pass to sentiment analysis
        social_data = None
        try:
            social_data = await news_service.get_social_sentiment(symbol)
        except Exception:
            pass

        return await analyze_sentiment(
            symbol=symbol,
            asset_type="stock",
            quote_data=dict(quote) if quote else None,
            technical_data=technical_data,
            social_data=social_data,
        )
    except Exception as e:
        logger.warning("AI sentiment for %s failed: %s", symbol, e)
        return None
