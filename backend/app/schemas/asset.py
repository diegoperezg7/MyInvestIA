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


# --- Portfolio Schemas ---


class AddHoldingRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=10)
    name: str = Field(min_length=1, max_length=100)
    type: AssetType
    quantity: float = Field(gt=0)
    avg_buy_price: float = Field(gt=0)


class UpdateHoldingRequest(BaseModel):
    quantity: float | None = Field(default=None, gt=0)
    avg_buy_price: float | None = Field(default=None, gt=0)


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


# --- Watchlist Schemas ---


class CreateWatchlistRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class UpdateWatchlistRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class AddWatchlistAssetRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=10)
    name: str = Field(min_length=1, max_length=100)
    type: AssetType


class Watchlist(BaseModel):
    id: str
    name: str
    assets: list[Asset] = []


class WatchlistList(BaseModel):
    watchlists: list[Watchlist] = []
    total: int = 0


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


# --- Market Overview Schemas ---


class MarketOverview(BaseModel):
    sentiment_index: float = 0.0
    top_gainers: list[Asset] = []
    top_losers: list[Asset] = []
    macro_indicators: list[MacroIndicator] = []


# --- Alert List Schemas ---


class AlertList(BaseModel):
    alerts: list[Alert] = []
    total: int = 0


# --- Market Data Schemas ---


class AssetQuote(BaseModel):
    symbol: str
    name: str
    price: float
    change_percent: float = 0.0
    volume: float = 0.0
    previous_close: float = 0.0
    market_cap: float = 0.0


class HistoricalDataPoint(BaseModel):
    date: str
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0


class HistoricalData(BaseModel):
    symbol: str
    period: str
    interval: str
    data: list[HistoricalDataPoint] = []


# --- Technical Analysis Schemas ---


class IndicatorSignal(BaseModel):
    value: float | None = None
    signal: str = "neutral"  # bullish, bearish, neutral


class RSIIndicator(IndicatorSignal):
    pass


class MACDIndicator(BaseModel):
    macd_line: float | None = None
    signal_line: float | None = None
    histogram: float | None = None
    signal: str = "neutral"


class SMAIndicator(BaseModel):
    sma_20: float | None = None
    sma_50: float | None = None
    signal: str = "neutral"


class EMAIndicator(BaseModel):
    ema_12: float | None = None
    ema_26: float | None = None
    signal: str = "neutral"


class BollingerBandsIndicator(BaseModel):
    upper: float | None = None
    middle: float | None = None
    lower: float | None = None
    bandwidth: float | None = None
    signal: str = "neutral"


class TechnicalAnalysis(BaseModel):
    symbol: str
    rsi: RSIIndicator = RSIIndicator()
    macd: MACDIndicator = MACDIndicator()
    sma: SMAIndicator = SMAIndicator()
    ema: EMAIndicator = EMAIndicator()
    bollinger_bands: BollingerBandsIndicator = BollingerBandsIndicator()
    overall_signal: str = "neutral"
    signal_counts: dict[str, int] = {"bullish": 0, "bearish": 0, "neutral": 0}
