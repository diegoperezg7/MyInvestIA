"""Screener schemas."""

from pydantic import BaseModel


class ScreenerRequest(BaseModel):
    market: str = "america"
    filters: dict = {}
    preset_id: str | None = None
    limit: int = 50


class ScreenerResult(BaseModel):
    symbol: str
    name: str = ""
    close: float = 0.0
    change: float = 0.0
    change_percent: float = 0.0
    volume: int = 0
    market_cap: float = 0.0
    recommendation: str = "neutral"


class ScreenerResponse(BaseModel):
    results: list[ScreenerResult] = []
    total: int = 0
    market: str = "america"
