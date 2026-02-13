"""Structured signal schemas for confidence scoring and rule-based analysis."""

from enum import Enum

from pydantic import BaseModel, Field


class SignalDirection(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class StructuredSignal(BaseModel):
    """A single analysis signal with direction and confidence."""
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=100.0)
    source: str  # e.g., "RSI", "MACD", "AI", "rule_engine"
    reasoning: str = ""


class SignalSummary(BaseModel):
    """Aggregated signal summary across oscillators and moving averages."""
    symbol: str
    overall: SignalDirection = SignalDirection.NEUTRAL
    overall_confidence: float = Field(ge=0.0, le=100.0, default=50.0)

    # Sub-ratings
    oscillators_rating: SignalDirection = SignalDirection.NEUTRAL
    oscillators_buy: int = 0
    oscillators_sell: int = 0
    oscillators_neutral: int = 0

    moving_averages_rating: SignalDirection = SignalDirection.NEUTRAL
    moving_averages_buy: int = 0
    moving_averages_sell: int = 0
    moving_averages_neutral: int = 0

    signals: list[StructuredSignal] = []

    # Technical data
    pivot_points: dict = {}
