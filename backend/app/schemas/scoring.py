"""Schemas for explainable asset scoring."""

from pydantic import BaseModel, Field


class ScoreComponent(BaseModel):
    name: str
    value: float = 0.0
    explanation: str = ""
    inputs_used: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    timestamp: str = ""
    sources: list[str] = Field(default_factory=list)
    weight_applied: float = 0.0


class AssetScoreQuote(BaseModel):
    price: float = 0.0
    change_percent: float = 0.0
    name: str = ""
    currency: str = "USD"


class AssetScoreResponse(BaseModel):
    symbol: str
    asset_type: str = "stock"
    quote: AssetScoreQuote = Field(default_factory=AssetScoreQuote)
    fundamentals_score: ScoreComponent = Field(default_factory=lambda: ScoreComponent(name="fundamentals_score"))
    technical_score: ScoreComponent = Field(default_factory=lambda: ScoreComponent(name="technical_score"))
    sentiment_score: ScoreComponent = Field(default_factory=lambda: ScoreComponent(name="sentiment_score"))
    macro_score: ScoreComponent = Field(default_factory=lambda: ScoreComponent(name="macro_score"))
    portfolio_fit_score: ScoreComponent = Field(default_factory=lambda: ScoreComponent(name="portfolio_fit_score"))
    total_score: ScoreComponent = Field(default_factory=lambda: ScoreComponent(name="total_score"))
    weights: dict[str, float] = Field(default_factory=dict)
    quant_overlay: dict = Field(default_factory=dict)
    portfolio_context: dict = Field(default_factory=dict)
    generated_at: str = ""
    decision_support_only: bool = True
    disclaimer: str = ""
