"""Schemas for AI explanation responses backed by structured analytics."""

from pydantic import BaseModel, Field


class StructuredAIAnalysisResponse(BaseModel):
    symbol: str
    summary: str
    signal: str = "neutral"
    confidence: float = 0.5
    confidence_label: str = "medium"
    warnings: list[str] = Field(default_factory=list)
    contradictory_signals: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    component_scores: dict[str, float] = Field(default_factory=dict)
    generated_at: str = ""
    decision_support_only: bool = True
