"""Tests for RL Trading Agent."""

import pytest
import asyncio
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, AsyncMock

from app.agents.rl_agent.agent import RLTradingAgent
from app.agents.rl_agent.indicators import TechnicalIndicators, SignalGenerator
from app.agents.rl_agent.scheduler import TradingScheduler, create_bot


class TestRLTradingAgent:
    """Tests for RLTradingAgent."""

    @pytest.fixture
    def agent(self):
        """Create agent instance."""
        return RLTradingAgent(
            symbol="BTC/USD",
            mode="paper",
            initial_balance=10000,
        )

    def test_agent_initialization(self, agent):
        """Test agent initializes correctly."""
        assert agent.symbol == "BTC/USD"
        assert agent.mode == "paper"
        assert agent.initial_balance == 10000
        assert agent.position == 0
        assert agent.trades == []

    def test_get_signal_insufficient_data(self, agent):
        """Test signal with insufficient data."""
        df = pd.DataFrame({"Close": [100, 101, 102]})

        signal = agent.get_signal(df)

        assert signal["action"] == "hold"
        assert signal["confidence"] == 0

    def test_get_signal_buy(self, agent):
        """Test buy signal generation."""
        # Create data with upward momentum
        prices = list(range(100, 120)) + [121, 122]
        df = pd.DataFrame({"Close": prices, "Volume": [1000] * len(prices)})

        signal = agent.get_signal(df)

        assert signal["action"] in ["buy", "hold"]
        assert "rsi" in signal
        assert "momentum" in signal

    def test_get_signal_sell(self, agent):
        """Test sell signal with stop loss."""
        agent.position = 1
        agent.entry_price = 100

        # Price drops 6% (triggering 5% stop loss)
        prices = [100] * 10 + [94] * 5
        df = pd.DataFrame({"Close": prices, "Volume": [1000] * len(prices)})

        signal = agent.get_signal(df)

        assert signal["action"] == "sell"
        assert "Stop" in signal["reason"]

    def test_execute_trade_buy(self, agent):
        """Test executing a buy trade."""
        trade = agent.execute_trade(
            signal={"action": "buy", "confidence": 0.8, "reason": "Test buy"},
            current_price=100,
            portfolio_value=10000,
        )

        assert trade is not None
        assert trade["action"] == "buy"
        assert agent.position == 1
        assert agent.entry_price == 100

    def test_execute_trade_sell(self, agent):
        """Test executing a sell trade."""
        agent.position = 1
        agent.entry_price = 100

        trade = agent.execute_trade(
            signal={"action": "sell", "confidence": 0.8, "reason": "Test sell"},
            current_price=110,
            portfolio_value=10000,
        )

        assert trade is not None
        assert trade["action"] == "sell"
        assert agent.position == 0

    def test_execute_trade_hold(self, agent):
        """Test executing a hold returns None."""
        trade = agent.execute_trade(
            signal={
                "action": "hold",
                "confidence": 0.5,
            },
            current_price=100,
            portfolio_value=10000,
        )

        assert trade is None

    def test_get_performance_empty(self, agent):
        """Test performance with no trades."""
        perf = agent.get_performance()

        assert perf["total_trades"] == 0
        assert perf["win_rate"] == 0

    def test_get_status(self, agent):
        """Test status retrieval."""
        status = agent.get_status()

        assert status["model_loaded"] == False
        assert status["mode"] == "paper"
        assert status["symbol"] == "BTC/USD"
        assert status["position"] == 0


class TestTechnicalIndicators:
    """Tests for TechnicalIndicators."""

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data."""
        np.random.seed(42)
        n = 100

        base_price = 100
        returns = np.random.randn(n) * 0.02
        close = base_price * np.exp(np.cumsum(returns))

        return pd.DataFrame(
            {
                "Open": close * 0.99,
                "High": close * 1.02,
                "Low": close * 0.98,
                "Close": close,
                "Volume": np.random.randint(1000, 10000, n),
            }
        )

    def test_sma(self, sample_data):
        """Test SMA calculation."""
        sma = TechnicalIndicators.sma(sample_data["Close"], 20)

        assert not sma.isna().all()
        assert len(sma) == len(sample_data)

    def test_ema(self, sample_data):
        """Test EMA calculation."""
        ema = TechnicalIndicators.ema(sample_data["Close"], 12)

        assert not ema.isna().all()

    def test_rsi(self, sample_data):
        """Test RSI calculation."""
        rsi = TechnicalIndicators.rsi(sample_data["Close"], 14)
        valid = rsi.dropna()

        assert not valid.empty
        assert (valid >= 0).all()
        assert (valid <= 100).all()

    def test_macd(self, sample_data):
        """Test MACD calculation."""
        macd, signal, hist = TechnicalIndicators.macd(sample_data["Close"])

        assert len(macd) == len(sample_data)
        assert len(signal) == len(sample_data)
        assert len(hist) == len(sample_data)

    def test_bollinger_bands(self, sample_data):
        """Test Bollinger Bands."""
        mid, upper, lower = TechnicalIndicators.bollinger_bands(sample_data["Close"])
        valid = pd.concat([mid, upper, lower], axis=1).dropna()
        upper_vs_mid = valid.iloc[:, 1] >= valid.iloc[:, 0]
        mid_vs_lower = valid.iloc[:, 0] >= valid.iloc[:, 2]

        assert upper_vs_mid.all()
        assert mid_vs_lower.all()

    def test_atr(self, sample_data):
        """Test ATR calculation."""
        atr = TechnicalIndicators.atr(
            sample_data["High"], sample_data["Low"], sample_data["Close"]
        )
        valid = atr.dropna()

        assert not valid.empty
        assert (valid >= 0).all()

    def test_stochastic(self, sample_data):
        """Test Stochastic calculation."""
        k, d = TechnicalIndicators.stochastic(
            sample_data["High"], sample_data["Low"], sample_data["Close"]
        )
        valid_k = k.dropna()

        assert not valid_k.empty
        assert (valid_k >= 0).all()
        assert (valid_k <= 100).all()


class TestSignalGenerator:
    """Tests for SignalGenerator."""

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data."""
        np.random.seed(42)
        n = 100

        base_price = 100
        returns = np.random.randn(n) * 0.02
        close = base_price * np.exp(np.cumsum(returns))

        return pd.DataFrame(
            {
                "Open": close * 0.99,
                "High": close * 1.02,
                "Low": close * 0.98,
                "Close": close,
                "Volume": np.random.randint(1000, 10000, n),
            }
        )

    def test_calculate_all(self, sample_data):
        """Test calculating all indicators."""
        generator = SignalGenerator()
        result = generator.calculate_all(sample_data)

        # Check expected columns exist
        assert "sma_20" in result.columns
        assert "rsi_14" in result.columns
        assert "macd" in result.columns
        assert "bb_position" in result.columns

    def test_generate_signals(self, sample_data):
        """Test signal generation."""
        generator = SignalGenerator()
        signals = generator.generate_signals(sample_data)

        assert "signal" in signals.columns
        assert "signal_strength" in signals.columns
        assert signals["signal"].isin([-1, 0, 1]).all()

    def test_get_latest_signal(self, sample_data):
        """Test getting latest signal."""
        generator = SignalGenerator()
        signal = generator.get_latest_signal(sample_data)

        assert "action" in signal
        assert "confidence" in signal
        assert "rsi_14" in signal
        assert signal["action"] in ["buy", "sell", "hold"]


class TestScheduler:
    """Tests for TradingScheduler."""

    @pytest.fixture
    def agent(self):
        """Create agent instance."""
        return RLTradingAgent(
            symbol="BTC/USD",
            mode="paper",
        )

    @pytest.mark.asyncio
    async def test_scheduler_initialization(self, agent):
        """Test scheduler initializes correctly."""
        scheduler = TradingScheduler(
            agent=agent,
            interval_minutes=30,
            symbols=["BTC-USD"],
        )

        assert scheduler.is_running == False
        assert scheduler.interval_minutes == 30
        assert scheduler.symbols == ["BTC-USD"]

    @pytest.mark.asyncio
    async def test_scheduler_get_status(self, agent):
        """Test scheduler status."""
        scheduler = TradingScheduler(
            agent=agent,
            interval_minutes=30,
        )

        status = scheduler.get_status()

        assert "is_running" in status
        assert "interval_minutes" in status
        assert "symbols" in status


class TestBot:
    """Tests for TradingBot."""

    def test_create_bot(self):
        """Test bot creation."""
        bot = create_bot({"mode": "paper"})

        assert bot.agent is not None
        assert bot.scheduler is not None

    def test_default_config(self):
        """Test default configuration."""
        bot = create_bot()

        assert bot.config["mode"] == "paper"
        assert bot.config["symbol"] == "BTC/USD"
        assert bot.config["initial_balance"] == 10000
