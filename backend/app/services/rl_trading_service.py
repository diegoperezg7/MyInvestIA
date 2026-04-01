"""
Service for RL Trading Agent integration.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import pandas as pd

from app.agents.rl_agent.agent import RLTradingAgent

# Per-user agent storage
_agents: Dict[str, RLTradingAgent] = {}

# File-based persistence
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / ".runtime" / "rl_agent"
DATA_DIR = Path(os.getenv("RL_AGENT_DATA_DIR", str(DEFAULT_DATA_DIR)))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _get_state_file(user_id: str) -> str:
    return str(DATA_DIR / f"state_{user_id}.json")


def _get_trades_file(user_id: str) -> str:
    return str(DATA_DIR / f"trades_{user_id}.json")


def _load_state(user_id: str) -> Optional[Dict]:
    """Load agent state from file."""
    try:
        path = _get_state_file(user_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _save_state(user_id: str, state: Dict):
    """Save agent state to file."""
    try:
        path = _get_state_file(user_id)
        with open(path, "w") as f:
            json.dump(state, f)
    except Exception:
        pass


def _load_trades(user_id: str) -> List[Dict]:
    """Load trades from file."""
    try:
        path = _get_trades_file(user_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_trades(user_id: str, trades: List[Dict]):
    """Save trades to file."""
    try:
        path = _get_trades_file(user_id)
        with open(path, "w") as f:
            json.dump(trades, f)
    except Exception:
        pass


async def init_agent(
    user_id: str,
    symbol: str = "BTC/USD",
    mode: str = "paper",
    checkpoint_path: Optional[str] = None,
    initial_balance: float = 10000,
    max_position_pct: float = 0.1,
    stop_loss_pct: float = 0.05,
    take_profit_pct: float = 0.10,
) -> Dict[str, Any]:
    """Initialize the RL trading agent."""

    # Try to load existing state from file
    saved_state = _load_state(user_id)

    agent = RLTradingAgent(
        symbol=symbol,
        mode=mode,
        checkpoint_path=checkpoint_path,
        initial_balance=initial_balance,
        max_position_pct=max_position_pct,
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct,
    )

    # Restore state if exists
    if saved_state:
        agent.symbol = saved_state.get("symbol", symbol)
        agent.mode = saved_state.get("mode", mode)
        agent.position = saved_state.get("position", 0)
        agent.entry_price = saved_state.get("entry_price", 0)
        agent.initial_balance = saved_state.get("initial_balance", initial_balance)
        agent.max_position_pct = saved_state.get("max_position_pct", max_position_pct)
        agent.stop_loss_pct = saved_state.get("stop_loss_pct", stop_loss_pct)
        agent.take_profit_pct = saved_state.get("take_profit_pct", take_profit_pct)

        # Load trades from file
        saved_trades = _load_trades(user_id)
        agent.trades = saved_trades

        # Rebuild equity curve from trades
        equity = agent.initial_balance
        for trade in saved_trades:
            pnl = trade.get("pnl", 0)
            equity = equity + pnl
            agent.equity_curve.append(equity)

    if checkpoint_path:
        agent.load_model(checkpoint_path)

    _agents[user_id] = agent

    # Save initial state
    _save_state(user_id, agent.get_status())

    return agent.get_status()


async def get_agent_status(user_id: str) -> Dict[str, Any]:
    """Get current agent status."""
    # Check in-memory first
    if user_id in _agents:
        return _agents[user_id].get_status()

    # Try to load from file
    saved_state = _load_state(user_id)
    if saved_state:
        return saved_state

    return {"model_loaded": False, "mode": "", "symbol": "", "position": 0}


async def get_signal(user_id: str, market_data: pd.DataFrame) -> Dict[str, Any]:
    """Get trading signal from agent."""
    # Ensure agent exists
    if user_id not in _agents:
        await init_agent(user_id)

    agent = _agents.get(user_id)
    return agent.get_signal(market_data)


async def execute_trade(
    user_id: str,
    market_data: pd.DataFrame,
    current_price: float,
    portfolio_value: float,
) -> Optional[Dict[str, Any]]:
    """Execute trade based on agent signal."""
    # Ensure agent exists
    if user_id not in _agents:
        await init_agent(user_id)

    agent = _agents.get(user_id)

    # Get signal
    signal = agent.get_signal(market_data)

    # Execute if not in shadow mode or if signal is strong
    if agent.mode == "live" and signal["confidence"] < 0.8:
        return {
            "signal": signal,
            "executed": False,
            "reason": "Low confidence - manual approval required",
        }

    # Execute trade
    trade = agent.execute_trade(signal, current_price, portfolio_value)

    # Save to file
    if trade:
        _save_state(user_id, agent.get_status())
        _save_trades(user_id, agent.trades)

    return {
        "signal": signal,
        "trade": trade,
        "executed": trade is not None,
    }


async def get_agent_performance(user_id: str) -> Dict[str, Any]:
    """Get agent performance metrics."""
    # Check in-memory first
    if user_id in _agents:
        return _agents[user_id].get_performance()

    # Try to load from file
    saved_state = _load_state(user_id)
    if saved_state:
        # Load agent with saved parameters
        await init_agent(
            user_id,
            symbol=saved_state.get("symbol", "BTC/USD"),
            mode=saved_state.get("mode", "paper"),
            initial_balance=saved_state.get("initial_balance", 10000),
            max_position_pct=saved_state.get("max_position_pct", 0.1),
            stop_loss_pct=saved_state.get("stop_loss_pct", 0.05),
            take_profit_pct=saved_state.get("take_profit_pct", 0.1),
        )
        return _agents[user_id].get_performance()

    # No saved state - create new
    await init_agent(user_id)
    return _agents[user_id].get_performance()


async def get_trade_history(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get trade history."""
    # Check in-memory first
    if user_id in _agents:
        agent = _agents.get(user_id)
        if agent and agent.trades:
            return agent.trades[-limit:]

    # Try to load from file
    saved_state = _load_state(user_id)
    if saved_state:
        await init_agent(
            user_id,
            symbol=saved_state.get("symbol", "BTC/USD"),
            mode=saved_state.get("mode", "paper"),
            initial_balance=saved_state.get("initial_balance", 10000),
            max_position_pct=saved_state.get("max_position_pct", 0.1),
            stop_loss_pct=saved_state.get("stop_loss_pct", 0.05),
            take_profit_pct=saved_state.get("take_profit_pct", 0.1),
        )
        agent = _agents.get(user_id)
        if agent and agent.trades:
            return agent.trades[-limit:]

    return _load_trades(user_id)[-limit:]


async def update_agent_mode(user_id: str, mode: str) -> Dict[str, Any]:
    """Update agent mode (paper/shadow/live)."""
    # Ensure agent exists
    if user_id not in _agents:
        await init_agent(user_id)

    agent = _agents.get(user_id)
    agent.mode = mode

    # Save state
    _save_state(user_id, agent.get_status())

    return {
        "mode": mode,
        "message": f"Agent mode changed to {mode}",
    }


async def close_position(user_id: str, current_price: float) -> Dict[str, Any]:
    """Force close current position."""
    # Ensure agent exists
    if user_id not in _agents:
        await init_agent(user_id)

    agent = _agents.get(user_id)

    if agent.position == 0:
        return {"executed": False, "reason": "No open position"}

    trade = agent.execute_trade(
        signal={
            "action": "sell",
            "confidence": 1.0,
            "reason": "Manual close",
        },
        current_price=current_price,
        portfolio_value=agent.initial_balance,
    )

    # Save to file
    if trade:
        _save_state(user_id, agent.get_status())
        _save_trades(user_id, agent.trades)

    return {
        "executed": True,
        "trade": trade,
    }
