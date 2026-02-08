from fastapi import APIRouter, HTTPException, Query

from app.schemas.asset import (
    Asset,
    AssetQuote,
    AssetType,
    BollingerBandsIndicator,
    EMAIndicator,
    HistoricalData,
    HistoricalDataPoint,
    MACDIndicator,
    MacroIndicator,
    MacroIndicatorDetail,
    MacroIntelligenceResponse,
    MacroSummary,
    MarketOverview,
    RSIIndicator,
    SMAIndicator,
    SentimentAnalysisResponse,
    TechnicalAnalysis,
)
from app.services.macro_intelligence import get_all_macro_indicators, get_macro_summary
from app.services.market_data import market_data_service
from app.services.sentiment_service import analyze_sentiment
from app.services.technical_analysis import compute_all_indicators

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/", response_model=MarketOverview)
async def get_market_overview():
    """Get market overview with top movers from major stocks."""
    movers = market_data_service.get_top_movers()

    gainers = [
        Asset(
            symbol=q["symbol"],
            name=q["name"],
            type=AssetType.STOCK,
            price=q["price"],
            change_percent=q["change_percent"],
            volume=q["volume"],
        )
        for q in movers.get("gainers", [])
    ]
    losers = [
        Asset(
            symbol=q["symbol"],
            name=q["name"],
            type=AssetType.STOCK,
            price=q["price"],
            change_percent=q["change_percent"],
            volume=q["volume"],
        )
        for q in movers.get("losers", [])
    ]

    # Fetch macro indicators for the overview
    macro_raw = get_all_macro_indicators()
    macro_indicators = [
        MacroIndicator(
            name=m["name"],
            value=m["value"],
            trend=m["trend"],
            impact_description=m["impact_description"],
        )
        for m in macro_raw
    ]

    return MarketOverview(
        sentiment_index=0.0,
        top_gainers=gainers,
        top_losers=losers,
        macro_indicators=macro_indicators,
    )


@router.get("/quote/{symbol}", response_model=AssetQuote)
async def get_quote(
    symbol: str,
    asset_type: AssetType | None = Query(default=None, description="Asset type hint"),
):
    """Get real-time quote for a single asset."""
    quote = await market_data_service.get_quote(symbol, asset_type)
    if not quote:
        raise HTTPException(status_code=404, detail=f"No data found for '{symbol.upper()}'")
    return AssetQuote(**quote)


@router.get("/history/{symbol}", response_model=HistoricalData)
async def get_history(
    symbol: str,
    period: str = Query(default="1mo", description="Time period: 1d,5d,1mo,3mo,6mo,1y,2y,5y,ytd,max"),
    interval: str = Query(default="1d", description="Interval: 1m,5m,15m,30m,1h,1d,1wk,1mo"),
):
    """Get historical OHLCV data for a stock/ETF."""
    records = market_data_service.get_history(symbol, period=period, interval=interval)
    if not records:
        raise HTTPException(status_code=404, detail=f"No history found for '{symbol.upper()}'")

    data_points = [HistoricalDataPoint(**r) for r in records]
    return HistoricalData(symbol=symbol.upper(), period=period, interval=interval, data=data_points)


@router.get("/analysis/{symbol}", response_model=TechnicalAnalysis)
async def get_technical_analysis(
    symbol: str,
    period: str = Query(default="6mo", description="History period for analysis"),
):
    """Compute technical indicators (RSI, MACD, SMA, EMA, Bollinger Bands) for an asset."""
    records = market_data_service.get_history(symbol, period=period, interval="1d")
    if not records or len(records) < 30:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient data for technical analysis on '{symbol.upper()}'"
        )

    closes = [r["close"] for r in records]
    indicators = compute_all_indicators(closes)

    return TechnicalAnalysis(
        symbol=symbol.upper(),
        rsi=RSIIndicator(**indicators["rsi"]),
        macd=MACDIndicator(**indicators["macd"]),
        sma=SMAIndicator(**indicators["sma"]),
        ema=EMAIndicator(**indicators["ema"]),
        bollinger_bands=BollingerBandsIndicator(**indicators["bollinger_bands"]),
        overall_signal=indicators["overall_signal"],
        signal_counts=indicators["signal_counts"],
    )


@router.get("/macro", response_model=MacroIntelligenceResponse)
async def get_macro_intelligence():
    """Get macro economic indicators (VIX, DXY, Treasury yields, Gold, Oil) with analysis."""
    raw_indicators = get_all_macro_indicators()
    summary = get_macro_summary(raw_indicators)

    indicators = [MacroIndicatorDetail(**m) for m in raw_indicators]

    return MacroIntelligenceResponse(
        indicators=indicators,
        summary=MacroSummary(**summary),
    )


@router.get("/sentiment/{symbol}", response_model=SentimentAnalysisResponse)
async def get_sentiment(
    symbol: str,
    asset_type: AssetType | None = Query(default=None, description="Asset type hint"),
):
    """Get AI-powered sentiment analysis for an asset.

    Uses Claude to analyze market sentiment based on available price data
    and technical indicators. Requires ANTHROPIC_API_KEY to be configured.
    """
    # Fetch quote and technical data to provide context
    quote = await market_data_service.get_quote(symbol, asset_type)
    quote_data = dict(quote) if quote else None

    technical_data = None
    records = market_data_service.get_history(symbol, period="6mo", interval="1d")
    if records and len(records) >= 30:
        closes = [r["close"] for r in records]
        technical_data = compute_all_indicators(closes)

    asset_type_str = asset_type.value if asset_type else "stock"
    result = await analyze_sentiment(
        symbol=symbol.upper(),
        asset_type=asset_type_str,
        quote_data=quote_data,
        technical_data=technical_data,
    )

    return SentimentAnalysisResponse(**result)
