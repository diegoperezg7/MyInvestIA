"""
RL Trading Agent router.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import time

from app.dependencies import get_current_user, AuthUser
from app.services import rl_trading_service


router = APIRouter(
    prefix="/rl-agent", tags=["rl-trading"], dependencies=[Depends(get_current_user)]
)

# Simple cache for BTC price (very short TTL)
_btc_price_cache = {
    "price": 0.0,
    "timestamp": 0.0,
    "cache_ttl": 3,  # 3 seconds cache only
}


def _get_cached_btc_price():
    """Get cached BTC price if still valid."""
    now = time.time()
    if (
        _btc_price_cache["price"] > 0
        and (now - _btc_price_cache["timestamp"]) < _btc_price_cache["cache_ttl"]
    ):
        return _btc_price_cache["price"], True
    # Reset cache if expired
    _btc_price_cache["price"] = 0.0
    _btc_price_cache["timestamp"] = 0.0
    return 0.0, False


def _set_cached_btc_price(price: float):
    """Cache BTC price."""
    _btc_price_cache["price"] = price
    _btc_price_cache["timestamp"] = time.time()


class InitAgentRequest(BaseModel):
    symbol: str = "BTC/USD"
    mode: str = "paper"  # paper | shadow | live
    checkpoint_path: Optional[str] = None
    initial_balance: float = 10000
    max_position_pct: float = 0.1
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.10


class ClosePositionRequest(BaseModel):
    current_price: float = 45000


class UpdateModeRequest(BaseModel):
    mode: str


class MarketDataInput(BaseModel):
    data: List[Dict[str, Any]]  # List of OHLCV candles
    current_price: float


@router.post("/init")
async def init_agent(req: InitAgentRequest, user: AuthUser = Depends(get_current_user)):
    """Initialize the RL trading agent."""
    try:
        result = await rl_trading_service.init_agent(
            user_id=user.id,
            symbol=req.symbol,
            mode=req.mode,
            checkpoint_path=req.checkpoint_path,
            initial_balance=req.initial_balance,
            max_position_pct=req.max_position_pct,
            stop_loss_pct=req.stop_loss_pct,
            take_profit_pct=req.take_profit_pct,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status(user: AuthUser = Depends(get_current_user)):
    """Get current agent status."""
    try:
        return await rl_trading_service.get_agent_status(user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/signal")
async def get_signal(
    market_data: MarketDataInput, user: AuthUser = Depends(get_current_user)
):
    """Get trading signal from agent."""
    try:
        import pandas as pd
        import numpy as np

        from app.services.market_data import market_data_service

        df = None
        current_price = market_data.current_price or 0

        # Always try to get fresh price (ignore cache for real-time)
        price_sources = []

        # 1. Try Binance first (no rate limit, very fast)
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    current_price = float(data.get("price", 0))
                    price_sources.append(f"Binance: ${current_price}")
        except Exception as e:
            print(f"Binance quote error: {e}")

        # 2. Try CoinGecko as backup
        if current_price == 0:
            try:
                btc_quote = await market_data_service.get_crypto_quote("BTC")
                if btc_quote and btc_quote.get("price"):
                    current_price = btc_quote.get("price")
                    price_sources.append(f"CoinGecko: ${current_price}")
            except Exception as e:
                print(f"CoinGecko quote error: {e}")

        # 3. If still no price, try yfinance as last resort
        if current_price == 0:
            try:
                from app.services.providers.yfinance_provider import (
                    YFinanceProvider,
                )

                yf = YFinanceProvider()
                quote = await yf.get_quote("BTC-USD")
                if quote and quote.get("price"):
                    current_price = quote.get("price")
                    price_sources.append(f"yfinance: ${current_price}")
            except Exception as e:
                print(f"yfinance quote error: {e}")

        if price_sources:
            print(f"BTC price from: {', '.join(price_sources)}")
            _set_cached_btc_price(current_price)

        # Get historical data from CoinGecko
        try:
            hist_data = await market_data_service.get_crypto_history("BTC", days=365)
            if hist_data and len(hist_data) > 0:
                df = pd.DataFrame(hist_data)
                # Use last price from history if current_price not available
                if current_price == 0 and len(df) > 0:
                    current_price = float(df.iloc[-1]["price"])
                    print(f"Using last historical price: ${current_price}")
                df = df.rename(columns={"price": "Close", "volume": "Volume"})
                df["Open"] = df["Close"]
                df["High"] = df["Close"]
                df["Low"] = df["Close"]
                if current_price > 0:
                    df.iloc[-1, df.columns.get_loc("Close")] = current_price
                df = df[["Open", "High", "Low", "Close", "Volume"]]
                print(f"BTC historical data: {len(df)} rows, price: ${current_price}")
        except Exception as e:
            print(f"Error fetching BTC history: {e}")

        if df is None or len(df) < 20:
            base_price = current_price
            dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq="D")

            np.random.seed(42)
            returns = np.random.normal(0.001, 0.02, 30)
            close = base_price * (1 + returns).cumprod()
            open_prices = close * (1 + np.random.normal(0, 0.01, 30))
            high = np.maximum(open_prices, close) * (
                1 + np.abs(np.random.normal(0, 0.01, 30))
            )
            low = np.minimum(open_prices, close) * (
                1 - np.abs(np.random.normal(0, 0.01, 30))
            )
            volume = np.random.randint(1000000, 10000000, 30)

            df = pd.DataFrame(
                {
                    "Open": open_prices,
                    "High": high,
                    "Low": low,
                    "Close": close,
                    "Volume": volume,
                }
            )
            print(f"Using sample data")

        signal = await rl_trading_service.get_signal(user.id, df)
        print(f"Signal generated: {signal.get('action')} - {signal.get('reason')}")

        # Enhance with Groq AI analysis
        try:
            from app.services.groq_service import groq_service

            if groq_service.is_available():
                ai_analysis = await groq_service.analyze_trading_signal(
                    price=current_price,
                    rsi=signal.get("rsi", 50),
                    momentum=signal.get("momentum", 0),
                    volume_ratio=signal.get("volume_ratio", 1),
                    position="long" if signal.get("position") == 1 else "flat",
                )
                # Merge AI analysis with signal
                if ai_analysis.get("reason"):
                    signal["reason"] = (
                        f"{signal.get('reason')}. AI: {ai_analysis.get('reason')}"
                    )
                if ai_analysis.get("confidence"):
                    # Blend with existing confidence
                    signal["confidence"] = (
                        signal.get("confidence", 0.5) + ai_analysis["confidence"]
                    ) / 2
        except Exception as e:
            print(f"Groq AI analysis error: {e}")

        # Prepare chart data for frontend - use last 100 candles
        chart_data = []
        if df is not None and len(df) > 0:
            from datetime import datetime, timedelta

            df_tail = df.tail(100).reset_index(drop=True)
            base_date = datetime.now() - timedelta(days=100)
            for i in range(len(df_tail)):
                row = df_tail.iloc[i]
                # Generate valid date string
                day_offset = int(i * 365 / 100)
                date_str = (base_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")
                chart_data.append(
                    {
                        "date": date_str,
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": float(row["Volume"]) if "Volume" in row else 0,
                    }
                )

        return {
            "signal": signal,
            "current_price": current_price,
            "chart_data": chart_data[-100:] if chart_data else [],  # Last 100 candles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trade")
async def execute_trade(
    market_data: MarketDataInput, user: AuthUser = Depends(get_current_user)
):
    """Execute trade based on agent signal."""
    try:
        import pandas as pd
        import numpy as np

        from app.services.market_data import market_data_service

        df = None
        current_price = market_data.current_price or 0

        # Get real-time BTC price from CoinGecko
        try:
            btc_quote = await market_data_service.get_crypto_quote("BTC")
            if btc_quote and btc_quote.get("price"):
                current_price = btc_quote.get("price")
                print(f"Real-time BTC price from CoinGecko: ${current_price}")
        except Exception as e:
            print(f"Error fetching BTC quote: {e}")

        # Get historical data from CoinGecko
        try:
            hist_data = await market_data_service.get_crypto_history("BTC", days=365)
            if hist_data and len(hist_data) > 0:
                df = pd.DataFrame(hist_data)
                df = df.rename(columns={"price": "Close", "volume": "Volume"})
                df["Open"] = df["Close"]
                df["High"] = df["Close"]
                df["Low"] = df["Close"]
                if current_price > 0:
                    df.iloc[-1, df.columns.get_loc("Close")] = current_price
                df = df[["Open", "High", "Low", "Close", "Volume"]]
        except Exception as e:
            print(f"Error fetching BTC history: {e}")

        if df is None or len(df) < 20:
            base_price = current_price
            np.random.seed(42)
            returns = np.random.normal(0.001, 0.02, 30)
            close = base_price * (1 + returns).cumprod()
            open_prices = close * (1 + np.random.normal(0, 0.01, 30))
            high = np.maximum(open_prices, close) * (
                1 + np.abs(np.random.normal(0, 0.01, 30))
            )
            low = np.minimum(open_prices, close) * (
                1 - np.abs(np.random.normal(0, 0.01, 30))
            )
            volume = np.random.randint(1000000, 10000000, 30)

            df = pd.DataFrame(
                {
                    "Open": open_prices,
                    "High": high,
                    "Low": low,
                    "Close": close,
                    "Volume": volume,
                }
            )

        result = await rl_trading_service.execute_trade(
            user_id=user.id,
            market_data=df,
            current_price=current_price,
            portfolio_value=10000,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance(user: AuthUser = Depends(get_current_user)):
    """Get agent performance metrics."""
    try:
        return await rl_trading_service.get_agent_performance(user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades")
async def get_trades(limit: int = 50, user: AuthUser = Depends(get_current_user)):
    """Get trade history."""
    try:
        return await rl_trading_service.get_trade_history(user.id, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mode")
async def update_mode(
    req: UpdateModeRequest, user: AuthUser = Depends(get_current_user)
):
    """Update agent mode."""
    if req.mode not in ["paper", "shadow", "live"]:
        raise HTTPException(status_code=400, detail="Invalid mode")

    try:
        return await rl_trading_service.update_agent_mode(user.id, req.mode)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/close-position")
async def close_position(
    req: ClosePositionRequest, user: AuthUser = Depends(get_current_user)
):
    """Force close current position."""
    try:
        return await rl_trading_service.close_position(user.id, req.current_price)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
