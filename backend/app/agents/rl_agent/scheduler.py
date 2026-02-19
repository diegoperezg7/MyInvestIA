"""
Automated Trading Scheduler.
Runs the RL agent at regular intervals.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
import json
import yfinance as yf

from app.agents.rl_agent.agent import RLTradingAgent
from app.agents.rl_agent.indicators import SignalGenerator

logger = logging.getLogger(__name__)


class TradingScheduler:
    """
    Scheduler for automated trading.
    Runs the trading strategy at regular intervals.
    """

    def __init__(
        self,
        agent: RLTradingAgent,
        interval_minutes: int = 30,
        symbols: List[str] = None,
    ):
        self.agent = agent
        self.interval_minutes = interval_minutes
        self.symbols = symbols or ["BTC-USD"]

        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.trade_history: List[Dict] = []

        self.signal_generator = SignalGenerator()

        # Callbacks
        self.on_signal: Optional[Callable] = None
        self.on_trade: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

    async def start(self):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        self.is_running = True
        logger.info(
            f"Starting trading scheduler (interval: {self.interval_minutes} min)"
        )

        while self.is_running:
            try:
                await self._run_cycle()
                await asyncio.sleep(self.interval_minutes * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in trading cycle: {e}")
                if self.on_error:
                    self.on_error(e)
                await asyncio.sleep(60)  # Wait 1 min on error

    async def stop(self):
        """Stop the scheduler."""
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Trading scheduler stopped")

    async def _run_cycle(self):
        """Run one trading cycle."""
        logger.info(f"=== Trading Cycle {datetime.now().isoformat()} ===")

        for symbol in self.symbols:
            try:
                await self._process_symbol(symbol)
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")

    async def _process_symbol(self, symbol: str):
        """Process a single symbol."""
        # Fetch data
        df = await self._fetch_data(symbol)

        if df is None or len(df) < 50:
            logger.warning(f"Insufficient data for {symbol}")
            return

        # Generate signals
        signal = self.signal_generator.get_latest_signal(df)

        logger.info(
            f"{symbol} Signal: {signal['action']} (conf: {signal['confidence']:.2%})"
        )

        # Notify signal callback
        if self.on_signal:
            self.on_signal(symbol, signal)

        # Check if we should trade
        if self.agent.mode == "paper" or (
            self.agent.mode == "live" and signal["confidence"] >= 0.8
        ):
            await self._execute_trade(symbol, signal, df)

    async def _fetch_data(self, symbol: str) -> Optional:
        """Fetch market data for symbol."""
        try:
            data = yf.download(symbol, period="90d", interval="1d", progress=False)

            if data.empty:
                return None

            # Flatten columns if needed
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            return data
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    async def _execute_trade(self, symbol: str, signal: Dict, df):
        """Execute a trade based on signal."""
        current_price = signal["price"]
        portfolio_value = self.agent.initial_balance

        # Get signal from agent
        agent_signal = self.agent.get_signal(df)

        # Combine signals
        if signal["action"] == agent_signal["action"]:
            final_action = signal["action"]
            confidence = (signal["confidence"] + agent_signal["confidence"]) / 2
        else:
            final_action = agent_signal["action"]
            confidence = agent_signal["confidence"]

        # Check stop loss
        if agent_signal["action"] == "sell":
            trade = self.agent.execute_trade(
                signal={
                    "action": "sell",
                    "confidence": 1.0,
                    "reason": "Signal: " + signal.get("reason", "Take profit"),
                },
                current_price=current_price,
                portfolio_value=portfolio_value,
            )
        elif final_action == "buy" and agent_signal.get("position", 0) == 0:
            trade = self.agent.execute_trade(
                signal={
                    "action": "buy",
                    "confidence": confidence,
                    "reason": f"Signal: RSI={signal['rsi_14']:.1f}, MACD={signal['macd']:.2f}",
                },
                current_price=current_price,
                portfolio_value=portfolio_value,
            )

        if trade and self.on_trade:
            self.on_trade(symbol, trade)

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "is_running": self.is_running,
            "interval_minutes": self.interval_minutes,
            "symbols": self.symbols,
            "total_cycles": len(self.trade_history),
            "agent_status": self.agent.get_status(),
        }


class TradingBot:
    """
    Complete trading bot with scheduler and persistence.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Initialize agent
        self.agent = RLTradingAgent(
            symbol=config.get("symbol", "BTC/USD"),
            mode=config.get("mode", "paper"),
            initial_balance=config.get("initial_balance", 10000),
            max_position_pct=config.get("max_position_pct", 0.1),
            stop_loss_pct=config.get("stop_loss_pct", 0.05),
            take_profit_pct=config.get("take_profit_pct", 0.10),
        )

        # Initialize scheduler
        self.scheduler = TradingScheduler(
            agent=self.agent,
            interval_minutes=config.get("interval_minutes", 30),
            symbols=config.get("symbols", ["BTC-USD"]),
        )

        # Setup callbacks
        self.scheduler.on_signal = self._on_signal
        self.scheduler.on_trade = self._on_trade
        self.scheduler.on_error = self._on_error

        # State file
        self.state_file = Path("data/trading_bot_state.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def _on_signal(self, symbol: str, signal: Dict):
        """Handle new signal."""
        logger.info(f"Signal received: {symbol} {signal['action']}")

    def _on_trade(self, symbol: str, trade: Dict):
        """Handle executed trade."""
        logger.info(f"Trade executed: {symbol} {trade}")
        self._save_state()

    def _on_error(self, error: Exception):
        """Handle error."""
        logger.error(f"Trading error: {error}")

    def _save_state(self):
        """Save bot state to file."""
        state = {
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent.get_status(),
            "performance": self.agent.get_performance(),
        }

        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def _load_state(self) -> bool:
        """Load bot state from file."""
        if not self.state_file.exists():
            return False

        try:
            with open(self.state_file, "r") as f:
                state = json.load(f)

            # Restore agent state
            self.agent.trades = state.get("agent", {}).get("trades", [])

            return True
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            return False

    async def start(self):
        """Start the trading bot."""
        logger.info("Starting Trading Bot...")

        # Try to restore previous state
        if self._load_state():
            logger.info("Restored previous state")

        # Start scheduler
        await self.scheduler.start()

    async def stop(self):
        """Stop the trading bot."""
        logger.info("Stopping Trading Bot...")
        await self.scheduler.stop()
        self._save_state()

    def get_status(self) -> Dict[str, Any]:
        """Get bot status."""
        return {
            "config": self.config,
            "scheduler": self.scheduler.get_status(),
            "performance": self.agent.get_performance(),
            "state_file": str(self.state_file),
        }


# Default configuration
DEFAULT_CONFIG = {
    "symbol": "BTC/USD",
    "mode": "paper",  # paper, shadow, live
    "initial_balance": 10000,
    "max_position_pct": 0.1,
    "stop_loss_pct": 0.05,
    "take_profit_pct": 0.10,
    "interval_minutes": 30,
    "symbols": ["BTC-USD", "ETH-USD"],
}


import pandas as pd


def create_bot(config: Optional[Dict] = None) -> TradingBot:
    """Factory function to create trading bot."""
    final_config = {**DEFAULT_CONFIG, **(config or {})}
    return TradingBot(final_config)
