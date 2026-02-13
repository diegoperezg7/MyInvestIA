"""Prediction response schema for the all-in-one prediction feature."""

from enum import Enum

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class PredictionResponse(BaseModel):
    symbol: str
    # Unified verdict
    verdict: Verdict = Verdict.NEUTRAL
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    # Section summaries
    technical_summary: dict = {}
    sentiment_summary: dict = {}
    macro_summary: dict = {}
    news_summary: dict = {}
    social_summary: dict = {}
    # AI prediction
    price_outlook: dict = {}
    ai_analysis: str = ""
    # Quantitative scoring engine results
    quant_scores: dict = {}
    generated_at: str = ""
