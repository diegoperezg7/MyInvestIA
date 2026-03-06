from enum import Enum

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    STOCK = "stock"
    ETF = "etf"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    PREDICTION = "prediction"


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
    source: str = "manual"
    connection_id: str | None = None


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
    market_cap: float | None = 0.0


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


# --- Chat / AI Schemas ---


class ChatMessage(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    context: str = ""


class ChatResponse(BaseModel):
    response: str
    model: str = "groq-llama-3.3-70b"


class AIAnalysisResponse(BaseModel):
    symbol: str
    summary: str
    signal: str = "neutral"
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


# --- Macro Intelligence Schemas ---


class MacroIndicatorDetail(BaseModel):
    name: str
    ticker: str = ""
    value: float
    change_percent: float = 0.0
    previous_close: float = 0.0
    trend: TrendDirection
    impact_description: str = ""
    category: str = ""


class MacroSummary(BaseModel):
    environment: str = "unknown"
    risk_level: str = "unknown"
    key_signals: list[str] = []


class MacroIntelligenceResponse(BaseModel):
    indicators: list[MacroIndicatorDetail] = []
    summary: MacroSummary = MacroSummary()


# --- Sentiment Analysis Schemas ---


class SentimentAnalysisResponse(BaseModel):
    symbol: str
    score: float = Field(ge=-1.0, le=1.0, default=0.0)
    label: SentimentLabel = SentimentLabel.NEUTRAL
    sources_count: int = 0
    narrative: str = ""
    key_factors: list[str] = []


# --- Alerts Engine Schemas ---


class NotifiedAlert(BaseModel):
    alert_id: str
    symbol: str | None = None
    title: str
    severity: str
    delivered: bool


class ScanAndNotifyResponse(BaseModel):
    alerts: list[Alert] = []
    notified: list[NotifiedAlert] = []
    total_alerts: int = 0
    total_notified: int = 0
    telegram_configured: bool = False


# --- Fundamentals Schemas ---


class CompanyInfo(BaseModel):
    name: str = ""
    sector: str = ""
    industry: str = ""
    market_cap: float = 0.0
    employees: int | None = None
    description: str = ""
    website: str = ""
    country: str = ""


class FinancialRatios(BaseModel):
    pe_trailing: float = 0.0
    pe_forward: float = 0.0
    price_to_book: float = 0.0
    price_to_sales: float = 0.0
    ev_to_ebitda: float = 0.0
    roe: float = 0.0
    debt_to_equity: float = 0.0
    current_ratio: float = 0.0
    profit_margins: float = 0.0
    operating_margins: float = 0.0
    gross_margins: float = 0.0
    dividend_yield: float = 0.0
    payout_ratio: float = 0.0
    beta: float = 0.0


class GrowthMetrics(BaseModel):
    revenue_growth: float = 0.0
    earnings_growth: float = 0.0
    revenue_history: list[dict] = []
    earnings_history: list[dict] = []


class PeerComparison(BaseModel):
    symbol: str
    name: str = ""
    pe_trailing: float = 0.0
    price_to_book: float = 0.0
    roe: float = 0.0
    profit_margins: float = 0.0
    market_cap: float = 0.0


class FundamentalsResponse(BaseModel):
    symbol: str
    company_info: CompanyInfo = CompanyInfo()
    ratios: FinancialRatios = FinancialRatios()
    growth: GrowthMetrics = GrowthMetrics()
    peers: list[PeerComparison] = []


# --- Economic Calendar Schemas ---


class EconomicEvent(BaseModel):
    date: str = ""
    time: str = ""
    event: str = ""
    country: str = ""
    impact: str = "low"  # low, medium, high
    forecast: float | None = None
    previous: float | None = None
    actual: float | None = None


class EarningsEvent(BaseModel):
    symbol: str = ""
    name: str = ""
    date: str = ""
    eps_estimate: float | None = None
    eps_actual: float | None = None
    revenue_estimate: float | None = None
    revenue_actual: float | None = None


class EconomicCalendarResponse(BaseModel):
    events: list[EconomicEvent] = []
    earnings: list[EarningsEvent] = []
    date_range: dict = {}


# --- Portfolio Risk Schemas ---


class PortfolioRiskMetrics(BaseModel):
    var_95: float = 0.0
    var_99: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    beta: float = 0.0
    max_drawdown: float = 0.0
    annual_volatility: float = 0.0
    daily_return_mean: float = 0.0


class ConcentrationRisk(BaseModel):
    positions: list[dict] = []
    top3_concentration: float = 0.0
    hhi_score: float = 0.0
    diversification_score: float = 0.0
    alerts: list[str] = []


class CorrelationData(BaseModel):
    symbols: list[str] = []
    matrix: list[list[float]] = []
    high_correlations: list[dict] = []


class StressTestScenario(BaseModel):
    name: str = ""
    description: str = ""
    market_drop: float = 0.0
    estimated_portfolio_loss: float = 0.0
    estimated_portfolio_loss_pct: float = 0.0


class PortfolioRiskResponse(BaseModel):
    metrics: PortfolioRiskMetrics = PortfolioRiskMetrics()
    concentration: ConcentrationRisk = ConcentrationRisk()
    correlation: CorrelationData = CorrelationData()
    stress_tests: list[StressTestScenario] = []
    portfolio_value: float = 0.0


# --- Sector Heatmap & Market Breadth Schemas ---


class SectorPerformance(BaseModel):
    symbol: str
    name: str
    performance_1d: float = 0.0
    performance_1w: float = 0.0
    performance_1m: float = 0.0
    market_cap_weight: float = 0.0


class SectorHeatmapResponse(BaseModel):
    sectors: list[SectorPerformance] = []
    last_updated: str = ""


class MarketBreadthIndicators(BaseModel):
    advancing: int = 0
    declining: int = 0
    unchanged: int = 0
    advance_decline_ratio: float = 0.0
    new_highs: int = 0
    new_lows: int = 0
    pct_above_sma50: float = 0.0
    pct_above_sma200: float = 0.0
    sentiment: str = "neutral"  # bullish, neutral, bearish
    last_updated: str = ""
