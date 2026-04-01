from app.services.news_intelligence import (
    build_social_sentiment_from_articles,
    deduplicate_articles,
    resolve_ticker_mentions,
    score_article,
)


def test_resolve_ticker_mentions_uses_aliases_and_symbols():
    article = {
        "headline": "Apple and Nvidia rally as Bitcoin ETF flows accelerate",
        "summary": "AAPL partners expand while $NVDA demand stays strong. BTC sentiment improves.",
        "related": "SPY BTC",
        "source_provider": "rss",
        "source_category": "news",
    }

    mentions = resolve_ticker_mentions(article)

    assert "AAPL" in mentions
    assert "NVDA" in mentions
    assert "BTC" in mentions
    assert "SPY" in mentions


def test_score_article_adds_pipeline_fields():
    article = {
        "headline": "$TSLA beats earnings estimates and stock rally extends",
        "summary": "Retail traders remain bullish on Tesla after the earnings beat.",
        "datetime": 1_700_000_000,
        "source_provider": "reddit",
        "source_category": "social",
        "score": 240,
        "num_comments": 81,
        "ai_analysis": {"impact_score": 8, "sentiment": "positive", "urgency": "high"},
    }

    scored = score_article(article, now_ts=1_700_003_600)

    assert scored["sentiment_score"] > 0
    assert scored["confidence"] > 0
    assert scored["relevance_score"] > 0
    assert "TSLA" in scored["ticker_mentions"]
    assert scored["retrieval_mode"] in {"public_api", "oauth"}


def test_deduplicate_articles_merges_similar_headlines():
    first = score_article(
        {
            "headline": "Breaking: Apple launches new AI features for iPhone",
            "summary": "Cupertino unveils new Apple Intelligence tools.",
            "datetime": 1_700_000_500,
            "url": "https://example.com/apple?utm_source=test",
            "source_provider": "rss",
            "source_category": "news",
        },
        now_ts=1_700_003_600,
    )
    second = score_article(
        {
            "headline": "Apple launches new AI features for iPhone users",
            "summary": "The iPhone maker expands its AI lineup.",
            "datetime": 1_700_000_400,
            "url": "https://example.com/apple",
            "source_provider": "gdelt",
            "source_category": "news",
        },
        now_ts=1_700_003_600,
    )

    deduped = deduplicate_articles([first, second])

    assert len(deduped) == 1
    assert deduped[0]["duplicate_group"].startswith("dup-")
    assert "AAPL" in deduped[0]["ticker_mentions"]


def test_build_social_sentiment_from_articles_aggregates_sources():
    articles = [
        score_article(
            {
                "headline": "$NVDA continues to rally",
                "summary": "Bullish momentum remains intact.",
                "datetime": 1_700_000_500,
                "source_provider": "reddit",
                "source_category": "social",
                "score": 100,
                "num_comments": 20,
                "related": "NVDA",
            },
            now_ts=1_700_003_600,
        ),
        score_article(
            {
                "headline": "StockTwits is bullish on NVDA",
                "summary": "Traders expect another breakout.",
                "datetime": 1_700_000_200,
                "source_provider": "stocktwits",
                "source_category": "social",
                "sentiment_label": "Bullish",
                "mentioned_symbols": ["NVDA"],
            },
            now_ts=1_700_003_600,
        ),
    ]

    result = build_social_sentiment_from_articles("NVDA", articles)

    assert result["symbol"] == "NVDA"
    assert result["total_mentions"] == 2
    assert result["combined_score"] > 0
    assert result["buzz_level"] in {"low", "moderate", "high", "viral"}

