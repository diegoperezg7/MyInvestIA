from datetime import datetime, timezone

from app.services.sentiment_engine import (
    _clip,
    _label,
    _time_decay,
    build_enhanced_sentiment,
    classify_text_sentiment,
    score_sentiment_item,
    _window_summary,
)
from app.services.news_intelligence import deduplicate_articles


def _article(
    headline: str,
    *,
    timestamp: int,
    provider: str = "rss",
    category: str = "news",
    related: str = "AAPL",
) -> dict:
    return {
        "headline": headline,
        "summary": headline,
        "datetime": timestamp,
        "source_provider": provider,
        "source": provider.upper(),
        "source_category": category,
        "related": related,
    }


def test_classify_text_sentiment_uses_heuristic_without_finbert():
    result = classify_text_sentiment("Apple beats earnings and stock rallies")
    assert result["provider"] in {"heuristic", "finbert"}
    assert result["score"] >= 0.0


def test_clip_clamps_values():
    assert _clip(0.5) == 0.5
    assert _clip(1.5) == 1.0
    assert _clip(-0.5) == -0.5
    assert _clip(-1.5) == -1.0
    assert _clip(0.5, lo=0.0, hi=0.8) == 0.5
    assert _clip(1.0, lo=0.0, hi=0.8) == 0.8


def test_label_bullish_neutral_bearish():
    assert _label(0.5) == "bullish"
    assert _label(0.2) == "bullish"
    assert _label(0.1) == "neutral"
    assert _label(-0.1) == "neutral"
    assert _label(-0.2) == "bearish"
    assert _label(-0.5) == "bearish"


def test_time_decay_reduces_old_items():
    decay_0h = _time_decay(0.0)
    decay_18h = _time_decay(18.0)
    decay_72h = _time_decay(72.0)
    assert decay_0h == 1.0
    assert 0.25 < decay_18h < 0.55
    assert 0.02 < decay_72h < 0.25


def test_window_summary_aggregates_correctly():
    now_dt = datetime.now(timezone.utc)
    items = [
        {
            "score": 0.5,
            "effective_weight": 0.8,
            "confidence": 0.7,
            "age_hours": 2.0,
            "label": "bullish",
        },
        {
            "score": -0.3,
            "effective_weight": 0.6,
            "confidence": 0.5,
            "age_hours": 5.0,
            "label": "bearish",
        },
    ]
    result = _window_summary(items, max_age_hours=24.0)
    assert result["count"] == 2
    assert result["bullish_items"] == 1
    assert result["bearish_items"] == 1
    assert -1.0 < result["score"] < 1.0


def test_window_summary_empty_returns_defaults():
    result = _window_summary([], max_age_hours=24.0)
    assert result["count"] == 0
    assert result["score"] == 0.0
    assert result["signal_strength"] == 0.0


def test_window_summary_respects_age_filters():
    now_dt = datetime.now(timezone.utc)
    items = [
        {"score": 0.8, "effective_weight": 1.0, "confidence": 0.9, "age_hours": 0.5},
        {"score": 0.4, "effective_weight": 1.0, "confidence": 0.9, "age_hours": 48.0},
    ]
    result_1h = _window_summary(items, max_age_hours=1.0)
    assert result_1h["count"] == 1
    result_24h = _window_summary(items, max_age_hours=24.0)
    assert result_24h["count"] == 1
    result_72h = _window_summary(items, max_age_hours=72.0)
    assert result_72h["count"] == 2


def test_score_sentiment_item_calculates_weights():
    now_dt = datetime.now(timezone.utc)
    article = _article("AAPL beats earnings", timestamp=int(now_dt.timestamp()))
    result = score_sentiment_item("AAPL", article, now_dt=now_dt)
    assert "effective_weight" in result
    assert "signal_strength" in result
    assert "noise_weight" in result
    assert result["effective_weight"] > 0.0
    assert result["score"] is not None


def test_score_sentiment_item_reduces_relevance_for_non_match():
    now_dt = datetime.now(timezone.utc)
    article = _article(
        "Market rallies on Fed news", timestamp=int(now_dt.timestamp()), related="SPY"
    )
    result_aapl = score_sentiment_item("AAPL", article, now_dt=now_dt)
    result_spy = score_sentiment_item("SPY", article, now_dt=now_dt)
    assert result_aapl["relevance"] < result_spy["relevance"]


def test_deduplicate_articles_removes_similar_headlines():
    now_ts = int(datetime.now(timezone.utc).timestamp())
    articles = [
        _article("Apple reports strong earnings", timestamp=now_ts),
        _article("Apple reports strong earnings", timestamp=now_ts - 3600),
        _article("Apple reports strong earnings for Q4", timestamp=now_ts - 7200),
        _article("AAPL beats expectations", timestamp=now_ts - 10800),
    ]
    deduped = deduplicate_articles(articles)
    assert len(deduped) <= 3


def test_deduplicate_articles_keeps_different_items():
    now_ts = int(datetime.now(timezone.utc).timestamp())
    articles = [
        _article("Apple launches new product", timestamp=now_ts),
        _article("Apple faces lawsuit", timestamp=now_ts),
    ]
    deduped = deduplicate_articles(articles)
    assert len(deduped) == 2


def test_build_enhanced_sentiment_tracks_temporal_shift_and_deduplicates():
    now_ts = int(datetime.now(timezone.utc).timestamp())
    articles = [
        _article("Apple faces lawsuit and downgrade", timestamp=now_ts - 72 * 3600),
        _article("Apple beats earnings and stock rallies", timestamp=now_ts - 3 * 3600),
        _article(
            "Breaking: Apple beats earnings and stock rallies",
            timestamp=now_ts - 2 * 3600,
        ),
        _article(
            "$AAPL sentiment on Reddit turns bullish",
            timestamp=now_ts - 3600,
            provider="reddit",
            category="social",
        ),
    ]

    result = build_enhanced_sentiment(
        "AAPL",
        articles,
        social_snapshot={
            "symbol": "AAPL",
            "combined_score": 0.35,
            "total_mentions": 12,
            "buzz_level": "high",
        },
    )

    assert result["symbol"] == "AAPL"
    assert result["total_data_points"] >= 2
    assert result["unified_label"] in {"bullish", "neutral"}
    assert result["recent_shift"] >= 0
    assert result["temporal_aggregation"]["24h"]["count"] >= 1
    assert result["source_breakdown"]


def test_build_enhanced_sentiment_handles_sparse_inputs():
    result = build_enhanced_sentiment(
        "TSLA",
        [],
        social_snapshot={
            "symbol": "TSLA",
            "combined_score": -0.4,
            "total_mentions": 18,
            "buzz_level": "high",
        },
    )

    assert result["symbol"] == "TSLA"
    assert result["unified_score"] < 0
    assert result["sources"]
    assert result["warnings"]


def test_build_enhanced_sentiment_calculates_momentum():
    now_ts = int(datetime.now(timezone.utc).timestamp())
    articles_old = [
        _article("Apple faces lawsuit", timestamp=now_ts - 72 * 3600),
    ]
    articles_recent = [
        _article("Apple beats earnings", timestamp=now_ts - 2 * 3600),
    ]
    result_old = build_enhanced_sentiment("AAPL", articles_old)
    result_recent = build_enhanced_sentiment("AAPL", articles_recent)
    combined_articles = articles_old + articles_recent
    result_combined = build_enhanced_sentiment("AAPL", combined_articles)
    assert "news_momentum" in result_combined
    assert "social_momentum" in result_combined
    assert "recent_shift" in result_combined


def test_build_enhanced_sentiment_detects_cross_source_divergence():
    now_ts = int(datetime.now(timezone.utc).timestamp())
    articles = [
        _article("Apple beats earnings and rallies", timestamp=now_ts),
    ]
    result = build_enhanced_sentiment(
        "AAPL",
        articles,
        ai_sentiment={"score": -0.6, "label": "bearish"},
        social_snapshot={
            "symbol": "AAPL",
            "combined_score": 0.7,
            "total_mentions": 15,
            "buzz_level": "high",
        },
    )
    assert "cross_source_divergence" in result
    if result["cross_source_divergence"] > 0.3:
        assert (
            any("diverg" in w.lower() for w in result["warnings"])
            or result["divergences"]
        )


def test_build_enhanced_sentiment_warns_on_low_confidence():
    result = build_enhanced_sentiment(
        "UNKNOWN",
        [],
        social_snapshot={
            "symbol": "UNKNOWN",
            "combined_score": 0.0,
            "total_mentions": 0,
            "buzz_level": "none",
        },
    )
    assert result["coverage_confidence"] < 0.3
    assert any(
        "coverage" in w.lower() or "thin" in w.lower() for w in result["warnings"]
    )


def test_build_enhanced_sentiment_includes_narratives():
    now_ts = int(datetime.now(timezone.utc).timestamp())
    articles = [
        _article("Apple launches new AI chip", timestamp=now_ts - 3600),
        _article("Apple expands data center", timestamp=now_ts - 7200),
    ]
    result = build_enhanced_sentiment("AAPL", articles)
    assert "top_narratives" in result
    assert isinstance(result["top_narratives"], list)
