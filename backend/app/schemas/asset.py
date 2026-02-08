from enum import Enum

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    STOCK = "stock"
    ETF = "etf"
    CRYPTO = "crypto"
    COMMODITY = "commodity"


class Asset(BaseModel):
    symbol: str
    name: str
    type: AssetType
    price: float = 0.0
    change_percent: float = 0.0
    volume: float = 0.0


class PortfolioHolding(BaseModel):
    asset: Asset
    quantity: float
    avg_buy_price: float
    current_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0


class Portfolio(BaseModel):
    total_value: float = 0.0
    daily_pnl: float = 0.0
    daily_pnl_percent: float = 0.0
    holdings: list[PortfolioHolding] = []


class Watchlist(BaseModel):
    id: str
    name: str
    assets: list[Asset] = []


class AlertType(str, Enum):
    PRICE = "price"
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"
    MACRO = "macro"
    MULTI_FACTOR = "multi_factor"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SuggestedAction(str, Enum):
    BUY = "buy"
    SELL = "sell"
    WAIT = "wait"
    MONITOR = "monitor"


class Alert(BaseModel):
    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_action: SuggestedAction
    created_at: str
    asset_symbol: str | None = None


class SentimentLabel(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class SentimentData(BaseModel):
    score: float = Field(ge=-1.0, le=1.0)
    label: SentimentLabel
    sources_count: int = 0
    narrative: str = ""


class TrendDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class MacroIndicator(BaseModel):
    name: str
    value: float
    trend: TrendDirection
    impact_description: str = ""
