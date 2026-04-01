"""Structured sentiment scoring and aggregation with optional FinBERT support."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.services.news_intelligence import (
    build_source_breakdown,
    build_social_sentiment_from_articles,
    cluster_narratives,
    deduplicate_articles,
    score_article,
)

logger = logging.getLogger(__name__)

try:
    from transformers import pipeline

    TRANSFORMERS_AVAILABLE = True
except Exception:
    pipeline = None
    TRANSFORMERS_AVAILABLE = False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().isoformat()


def _clip(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _label(score: float) -> str:
    if score >= 0.2:
        return "bullish"
    if score <= -0.2:
        return "bearish"
    return "neutral"


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def _age_hours(item: dict, now_dt: datetime) -> float:
    item_dt = _parse_timestamp(item.get("datetime") or item.get("published_at") or item.get("timestamp"))
    if item_dt is None:
        return 72.0
    return max(0.0, (now_dt - item_dt).total_seconds() / 3600.0)


def _time_decay(age_hours: float) -> float:
    half_life = max(float(getattr(settings, "sentiment_decay_half_life_hours", 18.0) or 18.0), 1.0)
    return math.exp(-math.log(2.0) * age_hours / half_life)


class _FinBertAdapter:
    def __init__(self):
        self._classifier = None

    @property
    def enabled(self) -> bool:
        return bool(getattr(settings, "sentiment_finbert_enabled", False)) and TRANSFORMERS_AVAILABLE

    def _get_classifier(self):
        if not self.enabled:
            return None
        if self._classifier is None:
            self._classifier = pipeline(
                "sentiment-analysis",
                model="ProsusAI/finbert",
                tokenizer="ProsusAI/finbert",
            )
        return self._classifier

    def classify(self, text: str) -> dict | None:
        if not text or not text.strip():
            return None
        classifier = self._get_classifier()
        if classifier is None:
            return None
        try:
            result = classifier(text[:512])[0]
            label = str(result.get("label", "neutral")).lower()
            confidence = float(result.get("score", 0.0) or 0.0)
            mapped_score = 0.0
            if "positive" in label:
                mapped_score = confidence
                label = "bullish"
            elif "negative" in label:
                mapped_score = -confidence
                label = "bearish"
            else:
                label = "neutral"
            return {
                "provider": "finbert",
                "score": round(_clip(mapped_score), 4),
                "label": label,
                "confidence": round(max(0.0, min(confidence, 1.0)), 4),
            }
        except Exception as exc:
            logger.warning("FinBERT classification failed: %s", exc)
            return None


_finbert_adapter = _FinBertAdapter()


def classify_text_sentiment(text: str, *, now_dt: datetime | None = None) -> dict:
    now_dt = now_dt or _utc_now()
    finbert_result = _finbert_adapter.classify(text)
    if finbert_result:
        return finbert_result

    pseudo = score_article(
        {
            "headline": text[:300],
            "summary": "",
            "datetime": int(now_dt.timestamp()),
            "source_provider": "rss",
            "source_category": "news",
        },
        now_ts=int(now_dt.timestamp()),
    )
    score = float(pseudo.get("sentiment_score", 0.0) or 0.0)
    confidence = float(pseudo.get("confidence", 0.0) or 0.0)
    return {
        "provider": "heuristic",
        "score": round(score, 4),
        "label": _label(score),
        "confidence": round(confidence, 4),
    }


def _ensure_scored_articles(articles: list[dict], *, now_dt: datetime) -> list[dict]:
    scored: list[dict] = []
    now_ts = int(now_dt.timestamp())
    for article in articles:
        working = dict(article)
        if "sentiment_score" not in working or "confidence" not in working:
            working = score_article(working, now_ts=now_ts)
        scored.append(working)
    return deduplicate_articles(scored)


def score_sentiment_item(
    symbol: str,
    article: dict,
    *,
    now_dt: datetime | None = None,
) -> dict:
    now_dt = now_dt or _utc_now()
    working = dict(article)
    if "sentiment_score" not in working or "confidence" not in working:
        working = score_article(working, now_ts=int(now_dt.timestamp()))

    mentions = set(working.get("ticker_mentions") or [])
    symbol_upper = symbol.upper()
    symbol_match = symbol_upper in mentions or symbol_upper in str(working.get("related") or "").upper()
    relevance = float(working.get("relevance_score", 0.2) or 0.2)
    if not symbol_match:
        relevance *= 0.45

    confidence = float(working.get("confidence", 0.15) or 0.15)
    score = float(working.get("sentiment_score", 0.0) or 0.0)
    age_hours = _age_hours(working, now_dt)
    time_decay = _time_decay(age_hours)
    category = str(working.get("source_category") or "news")
    category_weight = {"news": 1.0, "social": 0.82, "blog": 0.68}.get(category, 0.75)
    source_reliability = float(working.get("source_reliability", 0.55) or 0.55)

    effective_weight = confidence * relevance * time_decay * category_weight
    signal_strength = abs(score) * effective_weight
    noise_weight = (1.0 - min(abs(score) + confidence * 0.5, 1.0)) * effective_weight

    timestamp = _parse_timestamp(
        working.get("datetime") or working.get("published_at") or working.get("timestamp")
    )

    return {
        "id": working.get("id"),
        "headline": str(working.get("headline") or ""),
        "summary": str(working.get("summary") or ""),
        "score": round(_clip(score), 4),
        "label": _label(score),
        "confidence": round(max(0.0, min(confidence, 1.0)), 4),
        "relevance": round(max(0.0, min(relevance, 1.0)), 4),
        "age_hours": round(age_hours, 3),
        "time_decay": round(max(0.0, min(time_decay, 1.0)), 4),
        "effective_weight": round(max(0.0, effective_weight), 4),
        "signal_strength": round(max(0.0, signal_strength), 4),
        "noise_weight": round(max(0.0, noise_weight), 4),
        "source": str(working.get("source") or working.get("source_provider") or "unknown"),
        "source_provider": str(working.get("source_provider") or "unknown"),
        "source_category": category,
        "retrieval_mode": str(working.get("retrieval_mode") or "unknown"),
        "source_reliability": round(max(0.0, min(source_reliability, 1.0)), 4),
        "duplicate_group": working.get("duplicate_group"),
        "ticker_mentions": list(working.get("ticker_mentions") or []),
        "timestamp": timestamp.isoformat() if timestamp else _iso_now(),
    }


def _window_summary(
    items: list[dict],
    *,
    max_age_hours: float,
    min_age_hours: float = 0.0,
) -> dict:
    selected = [
        item
        for item in items
        if min_age_hours <= float(item.get("age_hours", 10_000.0) or 10_000.0) <= max_age_hours
    ]
    if not selected:
        return {
            "score": 0.0,
            "count": 0,
            "coverage": 0.0,
            "signal_strength": 0.0,
            "noise_weight": 0.0,
            "bullish_items": 0,
            "bearish_items": 0,
            "neutral_items": 0,
        }

    total_weight = sum(float(item.get("effective_weight", 0.0) or 0.0) for item in selected)
    weighted_score = (
        sum(float(item.get("score", 0.0) or 0.0) * float(item.get("effective_weight", 0.0) or 0.0) for item in selected)
        / total_weight
        if total_weight > 0
        else 0.0
    )
    coverage = sum(float(item.get("confidence", 0.0) or 0.0) for item in selected) / len(selected)
    return {
        "score": round(_clip(weighted_score), 4),
        "count": len(selected),
        "coverage": round(max(0.0, min(coverage, 1.0)), 4),
        "signal_strength": round(sum(float(item.get("signal_strength", 0.0) or 0.0) for item in selected), 4),
        "noise_weight": round(sum(float(item.get("noise_weight", 0.0) or 0.0) for item in selected), 4),
        "bullish_items": sum(1 for item in selected if item.get("label") == "bullish"),
        "bearish_items": sum(1 for item in selected if item.get("label") == "bearish"),
        "neutral_items": sum(1 for item in selected if item.get("label") == "neutral"),
    }


def _build_source_components(
    news_items: list[dict],
    social_items: list[dict],
    ai_sentiment: dict | None,
    social_snapshot: dict | None,
) -> list[dict]:
    components: list[dict] = []
    news_24h = _window_summary(news_items, max_age_hours=24.0)
    news_7d = _window_summary(news_items, max_age_hours=168.0)
    news_count = news_24h["count"] or news_7d["count"]
    if news_count:
        details = {
            "news_24h_count": news_24h["count"],
            "news_7d_count": news_7d["count"],
            "coverage_confidence": news_24h["coverage"] or news_7d["coverage"],
        }
        components.append(
            {
                "source_name": "Structured News Flow",
                "score": news_24h["score"] if news_24h["count"] else news_7d["score"],
                "weight": 0.60,
                "details": details,
            }
        )

    social_score = 0.0
    social_mentions = 0
    if social_snapshot:
        social_score = float(social_snapshot.get("combined_score", 0.0) or 0.0)
        social_mentions = int(social_snapshot.get("total_mentions", 0) or 0)
    elif social_items:
        social_window = _window_summary(social_items, max_age_hours=48.0)
        social_score = social_window["score"]
        social_mentions = social_window["count"]
    if social_mentions:
        components.append(
            {
                "source_name": "Social Pulse",
                "score": round(_clip(social_score), 4),
                "weight": 0.25,
                "details": {
                    "total_mentions": social_mentions,
                    "buzz_level": (social_snapshot or {}).get("buzz_level", "low"),
                },
            }
        )

    if ai_sentiment:
        components.append(
            {
                "source_name": "AI Narrative Overlay",
                "score": round(_clip(float(ai_sentiment.get("score", 0.0) or 0.0)), 4),
                "weight": 0.15,
                "details": {
                    "label": ai_sentiment.get("label", "neutral"),
                    "sources_count": ai_sentiment.get("sources_count", 0),
                },
            }
        )

    total_weight = sum(max(float(component["weight"]), 0.0) for component in components)
    if total_weight <= 1e-12:
        return []
    return [
        {
            **component,
            "weight": round(float(component["weight"]) / total_weight, 4),
        }
        for component in components
    ]


def _divergences(components: list[dict]) -> list[str]:
    divergences: list[str] = []
    for left_index in range(len(components)):
        for right_index in range(left_index + 1, len(components)):
            left = components[left_index]
            right = components[right_index]
            left_score = float(left.get("score", 0.0) or 0.0)
            right_score = float(right.get("score", 0.0) or 0.0)
            if abs(left_score - right_score) < 0.45:
                continue
            divergences.append(
                f"{left['source_name']} ({left_score:+.2f}) diverges from {right['source_name']} ({right_score:+.2f})."
            )
    return divergences[:6]


def _coverage_confidence(items: list[dict], source_components: list[dict]) -> float:
    if not items and not source_components:
        return 0.0
    article_confidence = (
        sum(float(item.get("confidence", 0.0) or 0.0) for item in items) / len(items)
        if items
        else 0.0
    )
    diversity = min(1.0, len({item.get("source_provider") for item in items}) / 4.0) if items else 0.0
    volume = min(1.0, len(items) / 10.0) if items else 0.0
    component_bonus = min(1.0, len(source_components) / 3.0)
    value = article_confidence * 0.55 + diversity * 0.15 + volume * 0.15 + component_bonus * 0.15
    return round(max(0.0, min(value, 0.99)), 4)


def build_enhanced_sentiment(
    symbol: str,
    articles: list[dict],
    *,
    ai_sentiment: dict | None = None,
    social_snapshot: dict | None = None,
    source_health: dict | None = None,
    now_dt: datetime | None = None,
) -> dict:
    """Build a structured multi-source sentiment snapshot for a symbol."""
    now_dt = now_dt or _utc_now()
    symbol_upper = symbol.upper()
    scored_articles = _ensure_scored_articles(articles, now_dt=now_dt)
    symbol_articles = [
        article
        for article in scored_articles
        if symbol_upper in set(article.get("ticker_mentions") or [])
    ]

    social_snapshot = social_snapshot or build_social_sentiment_from_articles(symbol_upper, symbol_articles)
    scored_items = [score_sentiment_item(symbol_upper, article, now_dt=now_dt) for article in symbol_articles]
    news_items = [item for item in scored_items if item.get("source_category") != "social"]
    social_items = [item for item in scored_items if item.get("source_category") == "social"]

    windows = {
        "1h": _window_summary(scored_items, max_age_hours=1.0),
        "24h": _window_summary(scored_items, max_age_hours=24.0),
        "7d": _window_summary(scored_items, max_age_hours=168.0),
    }
    prior_window = _window_summary(scored_items, min_age_hours=24.0, max_age_hours=96.0)
    source_components = _build_source_components(news_items, social_items, ai_sentiment, social_snapshot)

    unified_score = 0.0
    if source_components:
        unified_score = sum(
            float(component.get("score", 0.0) or 0.0) * float(component.get("weight", 0.0) or 0.0)
            for component in source_components
        )
    else:
        unified_score = windows["24h"]["score"] if windows["24h"]["count"] else windows["7d"]["score"]
    unified_score = round(_clip(unified_score), 4)

    signal_strength = sum(float(item.get("signal_strength", 0.0) or 0.0) for item in scored_items)
    noise_weight = sum(float(item.get("noise_weight", 0.0) or 0.0) for item in scored_items)
    signal_to_noise = round(signal_strength / max(noise_weight, 1e-6), 4) if scored_items else 0.0

    news_recent = _window_summary(news_items, max_age_hours=24.0)
    news_prior = _window_summary(news_items, min_age_hours=24.0, max_age_hours=96.0)
    news_momentum = round(_clip(news_recent["score"] - news_prior["score"]), 4)

    social_recent = _window_summary(social_items, max_age_hours=24.0)
    social_prior = _window_summary(social_items, min_age_hours=24.0, max_age_hours=96.0)
    base_social_momentum = social_recent["score"] - social_prior["score"]
    if not social_items and social_snapshot and social_snapshot.get("total_mentions", 0):
        base_social_momentum = float(social_snapshot.get("combined_score", 0.0) or 0.0) * min(
            1.0,
            float(social_snapshot.get("total_mentions", 0) or 0.0) / 20.0,
        )
    social_momentum = round(_clip(base_social_momentum), 4)
    recent_shift = round(_clip(windows["24h"]["score"] - prior_window["score"]), 4)

    divergences = _divergences(source_components)
    coverage_confidence = _coverage_confidence(scored_items, source_components)
    warnings: list[str] = []
    if coverage_confidence < 0.2:
        warnings.append("Coverage is thin; sentiment should be treated as low confidence.")
    if signal_to_noise < 1.0 and scored_items:
        warnings.append("Recent flow is noisy; signal quality is weaker than usual.")
    if divergences:
        warnings.append("Different sentiment sources are currently conflicting.")
    if scored_items and len({item.get("source_provider") for item in scored_items}) == 1:
        warnings.append("Sentiment relies on a single source family.")

    top_items = sorted(
        scored_items,
        key=lambda item: (float(item.get("effective_weight", 0.0) or 0.0), abs(float(item.get("score", 0.0) or 0.0))),
        reverse=True,
    )[:10]

    return {
        "symbol": symbol_upper,
        "unified_score": unified_score,
        "unified_label": _label(unified_score),
        "sources": source_components,
        "divergences": divergences,
        "coverage_confidence": coverage_confidence,
        "news_momentum": news_momentum,
        "social_momentum": social_momentum,
        "recent_shift": recent_shift,
        "signal_to_noise": signal_to_noise,
        "noise_ratio": round(noise_weight / max(signal_strength + noise_weight, 1e-6), 4) if scored_items else 0.0,
        "temporal_aggregation": windows,
        "items": top_items,
        "top_narratives": cluster_narratives(symbol_articles, limit=4),
        "source_breakdown": build_source_breakdown(symbol_articles),
        "cross_source_divergence": round(
            math.sqrt(
                sum(
                    (
                        float(component.get("score", 0.0) or 0.0)
                        - (sum(float(c.get("score", 0.0) or 0.0) for c in source_components) / max(len(source_components), 1))
                    )
                    ** 2
                    for component in source_components
                )
                / max(len(source_components), 1)
            ),
            4,
        )
        if source_components
        else 0.0,
        "source_health": source_health or {},
        "total_data_points": len(symbol_articles),
        "warnings": warnings,
        "classifier": {
            "provider": "finbert" if _finbert_adapter.enabled else "heuristic",
            "available": bool(_finbert_adapter.enabled),
        },
        "generated_at": now_dt.isoformat(),
    }
