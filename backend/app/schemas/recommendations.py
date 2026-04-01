"""Schemas for AI recommendations engine."""

from enum import Enum

from pydantic import BaseModel


class RecommendationCategory(str, Enum):
    opportunity = "opportunity"
    risk_alert = "risk_alert"
    rebalance = "rebalance"
    trend = "trend"
    macro_shift = "macro_shift"
    social_signal = "social_signal"
    earnings_watch = "earnings_watch"
    sector_rotation = "sector_rotation"


class RecommendationUrgency(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Recommendation(BaseModel):
    category: RecommendationCategory
    title: str
    reasoning: str
    confidence: float  # 0.0-1.0
    tickers: list[str]
    action: str
    urgency: RecommendationUrgency
    inbox_item_id: str | None = None
    why_now: str = ""
    horizon: str = "medium"


class RecommendationsResponse(BaseModel):
    market_mood: str  # Executive summary, 2 sentences
    mood_score: float  # -1.0 to 1.0
    recommendations: list[Recommendation]
    generated_at: str
