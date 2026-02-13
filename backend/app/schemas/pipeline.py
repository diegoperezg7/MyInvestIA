"""Pipeline schemas for multi-step analysis with SSE progress."""

from enum import Enum

from pydantic import BaseModel, Field


class PipelineStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStep(BaseModel):
    """A single step in the analysis pipeline."""
    id: str
    name: str
    description: str
    status: PipelineStepStatus = PipelineStepStatus.PENDING
    result: dict | None = None
    error: str | None = None
    duration_ms: int | None = None


class PipelineStatus(BaseModel):
    """Overall pipeline status sent via SSE."""
    symbol: str
    current_step: int = 0
    total_steps: int = 7
    steps: list[PipelineStep] = []
    completed: bool = False
    final_analysis: str | None = None
    signal: str = "neutral"
    confidence: float = 0.5


PIPELINE_STEPS = [
    {"id": "quote", "name": "Market Data", "description": "Fetching current price and volume"},
    {"id": "history", "name": "Historical Data", "description": "Loading price history"},
    {"id": "technicals", "name": "Technical Analysis", "description": "Computing RSI, MACD, SMA, EMA, Bollinger Bands"},
    {"id": "signals", "name": "Signal Aggregation", "description": "Generating buy/sell signals"},
    {"id": "sentiment", "name": "Sentiment Analysis", "description": "Analyzing market sentiment"},
    {"id": "macro", "name": "Macro Context", "description": "Evaluating macro environment"},
    {"id": "synthesis", "name": "AI Synthesis", "description": "Generating final analysis"},
]
