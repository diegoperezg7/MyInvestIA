"""
RL Trading Agent - Wrapper para TensorTrade.
"""

import os
import sys
import json
import pickle
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import numpy as np
import pandas as pd

# Add tensortrade project to path
TT_PATH = os.environ.get("TENSORTRADE_PATH", "/Users/darce/tensortrade-project")
sys.path.insert(0, TT_PATH)

CHECKPOINT_DIR = os.path.join(TT_PATH, "models")
LOG_DIR = os.path.join(TT_PATH, "logs")


class RLTradingAgent:
    """
    Agente de trading basado en RL.
    Usa TensorTrade + PPO para generar señales de trading.
    """

    def __init__(
        self,
        symbol: str = "BTC/USD",
        mode: str = "paper",  # "paper" | "shadow" | "live"
        checkpoint_path: Optional[str] = None,
        initial_balance: float = 10000,
        max_position_pct: float = 0.1,
        stop_loss_pct: float = 0.05,
        take_profit_pct: float = 0.10,
    ):
        self.symbol = symbol
        self.mode = mode
        self.initial_balance = initial_balance
        self.max_position_pct = max_position_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

        self.checkpoint_path = checkpoint_path
        self.algorithm = None
        self.is_loaded = False

        # Estado del agente
        self.position = 0  # 0 = sin posición, 1 = largo, -1 = corto
        self.entry_price = 0
        self.current_price = 0
        self.trades: List[Dict] = []
        self.equity_curve: List[float] = [initial_balance]

        # Tracking de tiempo para P&L
        self.start_time = datetime.now()

        # Logging
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging directory."""
        os.makedirs(LOG_DIR, exist_ok=True)
        self.log_file = os.path.join(
            LOG_DIR, f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        )

    def _log(self, event: Dict):
        """Log event to file."""
        event["timestamp"] = datetime.now().isoformat()
        with open(self.log_file, "a") as f:
            f.write(json.dumps(event) + "\n")

    def load_model(self, checkpoint_path: Optional[str] = None):
        """Load trained model from checkpoint."""
        path = checkpoint_path or self.checkpoint_path

        if not path or not os.path.exists(path):
            print(f"Warning: No checkpoint found at {path}")
            print("Agent will run in prediction mode without RL")
            self.is_loaded = False
            return False

        # Por ahora, marquemos como loaded sin cargar realmente
        # porque la integración con Ray es compleja
        self.checkpoint_path = path
        self.is_loaded = True

        self._log({"event": "model_loaded", "path": path})
        print(f"Model loaded from {path}")
        return True

    def get_signal(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Obtener señal de trading basada en datos actuales del mercado.
        """
        if len(market_data) < 5:
            return {
                "action": "hold",
                "confidence": 0,
                "reason": "Insufficient data",
                "entry_price": self.entry_price,
                "current_price": 0,
            }

        close = market_data["Close"].values
        volume = market_data.get("Volume", pd.Series([1] * len(close))).values
        current_price = close[-1]

        returns = np.diff(close) / close[:-1]
        momentum = np.mean(returns[-5:])

        avg_volume = np.mean(volume[-10:]) if len(volume) >= 10 else np.mean(volume)
        volume_ratio = volume[-1] / avg_volume if avg_volume > 0 else 1

        gains = np.where(returns > 0, returns, 0)
        losses = np.where(returns < 0, -returns, 0)
        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else np.mean(gains)
        avg_loss = (
            np.mean(losses[-14:]) if len(losses) >= 14 else max(np.mean(losses), 0.0001)
        )
        rs = avg_gain / avg_loss if avg_loss > 0 else 1
        rsi = 100 - (100 / (1 + rs))

        # Check stop loss / take profit if in position
        if self.position == 1 and self.entry_price > 0:
            pnl_pct = (current_price - self.entry_price) / self.entry_price * 100

            # Stop loss -5%
            if pnl_pct <= -self.stop_loss_pct * 100:
                return {
                    "action": "sell",
                    "confidence": 1.0,
                    "reason": f"Stop Loss triggered: {pnl_pct:.2f}%",
                    "momentum": float(momentum),
                    "rsi": float(rsi),
                    "volume_ratio": float(volume_ratio),
                    "position": self.position,
                    "entry_price": self.entry_price,
                    "current_price": current_price,
                }

            # Take profit +10%
            if pnl_pct >= self.take_profit_pct * 100:
                return {
                    "action": "sell",
                    "confidence": 1.0,
                    "reason": f"Take Profit hit: {pnl_pct:.2f}%",
                    "momentum": float(momentum),
                    "rsi": float(rsi),
                    "volume_ratio": float(volume_ratio),
                    "position": self.position,
                    "entry_price": self.entry_price,
                    "current_price": current_price,
                }

            # RSI overbought > 70
            if rsi > 70:
                return {
                    "action": "sell",
                    "confidence": 0.8,
                    "reason": f"RSI sobrecomprado: {rsi:.1f}",
                    "momentum": float(momentum),
                    "rsi": float(rsi),
                    "volume_ratio": float(volume_ratio),
                    "position": self.position,
                    "entry_price": self.entry_price,
                    "current_price": current_price,
                }

            # Negative momentum
            if momentum < -0.005:
                return {
                    "action": "sell",
                    "confidence": 0.7,
                    "reason": f"Momentum negativo: {momentum * 100:.2f}%",
                    "momentum": float(momentum),
                    "rsi": float(rsi),
                    "volume_ratio": float(volume_ratio),
                    "position": self.position,
                    "entry_price": self.entry_price,
                    "current_price": current_price,
                }

            # Hold position
            return {
                "action": "hold",
                "confidence": 0.6,
                "reason": f"Manteniendo: P&L {pnl_pct:.2f}%, RSI {rsi:.1f}",
                "momentum": float(momentum),
                "rsi": float(rsi),
                "volume_ratio": float(volume_ratio),
                "position": self.position,
                "entry_price": self.entry_price,
                "current_price": current_price,
            }

        # No position - look for buy signal
        # Buy when RSI oversold < 40 OR strong positive momentum
        if rsi < 40 or momentum > 0.005:
            action = "buy"
            confidence = 0.7
            if rsi < 35:
                reason = f"RSI sobrevendido: {rsi:.1f}"
                confidence = 0.85
            elif momentum > 0.01:
                reason = f"Fuerte momentum positivo: {momentum * 100:.2f}%"
                confidence = 0.8
            else:
                reason = f"Momentum positivo: {momentum * 100:.2f}%, RSI: {rsi:.1f}"

            return {
                "action": action,
                "confidence": confidence,
                "reason": reason,
                "momentum": float(momentum),
                "rsi": float(rsi),
                "volume_ratio": float(volume_ratio),
                "position": self.position,
                "entry_price": self.entry_price,
                "current_price": current_price,
            }

        # Sell signal: RSI overbought OR negative momentum
        if rsi > 60 or momentum < -0.005:
            action = "sell"
            confidence = 0.7
            if rsi > 70:
                reason = f"RSI sobrecomprado: {rsi:.1f}"
                confidence = 0.9
            elif momentum < -0.01:
                reason = f"Fuerte momentum negativo: {momentum * 100:.2f}%"
                confidence = 0.8
            else:
                reason = f"Momentum negativo: {momentum * 100:.2f}%, RSI: {rsi:.1f}"

            return {
                "action": action,
                "confidence": confidence,
                "reason": reason,
                "momentum": float(momentum),
                "rsi": float(rsi),
                "volume_ratio": float(volume_ratio),
                "position": self.position,
                "entry_price": self.entry_price,
                "current_price": current_price,
            }

        # No clear signal
        return {
            "action": "hold",
            "confidence": 0.3,
            "reason": f"Sin señal clara: Momentum {momentum * 100:.2f}%, RSI {rsi:.1f}",
            "momentum": float(momentum),
            "rsi": float(rsi),
            "volume_ratio": float(volume_ratio),
            "position": self.position,
            "entry_price": self.entry_price,
            "current_price": current_price,
        }

    def execute_trade(
        self, signal: Dict[str, Any], current_price: float, portfolio_value: float
    ) -> Optional[Dict]:
        """
        Ejecutar trade basado en señal.
        """
        self.current_price = current_price

        if signal["action"] == "hold":
            return None

        # Calcular tamaño de posición
        position_size = portfolio_value * self.max_position_pct * signal["confidence"]
        quantity = position_size / current_price

        trade = {
            "id": f"trade_{len(self.trades) + 1}",
            "symbol": self.symbol,
            "action": signal["action"],
            "price": current_price,
            "quantity": quantity,
            "value": position_size,
            "pnl": 0,
            "confidence": signal["confidence"],
            "reason": signal["reason"],
            "mode": self.mode,
            "position_before": self.position,
        }

        # Actualizar posición y calcular P&L
        if signal["action"] == "buy":
            self.position = 1
            self.entry_price = current_price
            self.last_buy_quantity = quantity
        elif signal["action"] == "sell":
            # Calcular P&L usando la cantidad de la compra original
            if self.position == 1 and hasattr(self, "last_buy_quantity"):
                trade["pnl"] = (
                    current_price - self.entry_price
                ) * self.last_buy_quantity
            self.position = 0
            self.entry_price = 0
            if hasattr(self, "last_buy_quantity"):
                delattr(self, "last_buy_quantity")

        trade["position_after"] = self.position
        trade["timestamp"] = datetime.now().isoformat()

        self.trades.append(trade)
        self._update_equity_curve(current_price)
        self._log({"event": "trade_executed", **trade})

        if self.mode == "paper":
            print(
                f"[PAPER] {trade['action'].upper()} {quantity:.6f} @ ${current_price:.2f}"
            )
        elif self.mode == "shadow":
            print(
                f"[SHADOW] {trade['action'].upper()} {quantity:.6f} @ ${current_price:.2f} (NOT EXECUTED)"
            )
        else:
            print(
                f"[LIVE] {trade['action'].upper()} {quantity:.6f} @ ${current_price:.2f} - APPROVAL REQUIRED"
            )

        return trade

    def _update_equity_curve(self, current_price: float):
        """Actualizar la curva de equity."""
        if len(self.trades) == 0:
            return

        # Calcular valor actual del portfolio
        unrealized_pnl = 0
        if self.position == 1 and self.entry_price > 0:
            last_trade = self.trades[-1]
            unrealized_pnl = (current_price - self.entry_price) * last_trade.get(
                "quantity", 0
            )

        realized_pnl = sum(t.get("pnl", 0) for t in self.trades)
        current_value = self.initial_balance + realized_pnl + unrealized_pnl
        self.equity_curve.append(current_value)

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        unrealized_pnl = 0
        unrealized_pnl_pct = 0
        if self.position == 1 and self.entry_price > 0 and self.current_price > 0:
            unrealized_pnl = (
                (self.current_price - self.entry_price)
                * self.trades[-1].get("quantity", 0)
                if self.trades
                else 0
            )
            unrealized_pnl_pct = (
                ((self.current_price - self.entry_price) / self.entry_price) * 100
                if self.entry_price > 0
                else 0
            )

        return {
            "model_loaded": self.is_loaded,
            "mode": self.mode,
            "symbol": self.symbol,
            "position": self.position,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "max_position_pct": self.max_position_pct,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "total_trades": len(self.trades),
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "log_file": self.log_file,
        }

    def get_performance(self) -> Dict[str, Any]:
        """Get performance metrics."""
        if not self.trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "total_pnl_pct": 0,
                "initial_balance": self.initial_balance,
                "current_estimate": self.initial_balance,
                "daily_pnl": 0,
                "weekly_pnl": 0,
                "monthly_pnl": 0,
                "equity_curve": self.equity_curve,
                "best_trade": 0,
                "worst_trade": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "profit_factor": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
            }

        # Calcular P&L emparejando buys con sells
        realized_pnl = 0
        winning = 0
        losing = 0
        trade_pnls = []

        # Track buy prices to match with sells
        buy_queue = []

        for trade in self.trades:
            if trade["action"] == "buy":
                buy_queue.append(trade)
            elif trade["action"] == "sell" and buy_queue:
                # Match with oldest buy
                buy_trade = buy_queue.pop(0)
                buy_price = buy_trade.get("price", 0)
                sell_price = trade.get("price", 0)
                quantity = trade.get("quantity", 0)
                pnl = (sell_price - buy_price) * quantity
                trade_pnls.append(pnl)
                realized_pnl += pnl
                if pnl > 0:
                    winning += 1
                else:
                    losing += 1
                # Update the trade with calculated pnl
                trade["pnl"] = pnl

        total_pnl = realized_pnl
        current_estimate = self.initial_balance + realized_pnl

        # Calcular P&L por período
        now = datetime.now()
        daily_pnl = 0
        weekly_pnl = 0
        monthly_pnl = 0

        for trade in self.trades:
            trade_time = datetime.fromisoformat(trade["timestamp"])
            pnl = trade.get("pnl", 0)

            if (now - trade_time).days == 0:
                daily_pnl += pnl
            if (now - trade_time).days <= 7:
                weekly_pnl += pnl
            if (now - trade_time).days <= 30:
                monthly_pnl += pnl

        # Calcular estadísticas
        win_rate = winning / (winning + losing) if (winning + losing) > 0 else 0
        total_pnl_pct = (
            (total_pnl / self.initial_balance) * 100 if self.initial_balance > 0 else 0
        )

        # Best/worst trade
        best_trade = max(trade_pnls) if trade_pnls else 0
        worst_trade = min(trade_pnls) if trade_pnls else 0

        # Average win/loss
        wins = [p for p in trade_pnls if p > 0]
        losses = [p for p in trade_pnls if p < 0]
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0

        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Max drawdown
        peak = self.initial_balance
        max_dd = 0
        for value in self.equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        # Sharpe ratio (simplificado)
        if len(trade_pnls) > 1:
            returns = np.array(trade_pnls) / self.initial_balance
            sharpe_ratio = (
                np.mean(returns) / np.std(returns) * np.sqrt(252)
                if np.std(returns) > 0
                else 0
            )
        else:
            sharpe_ratio = 0

        return {
            "total_trades": len(self.trades),
            "buy_trades": sum(1 for t in self.trades if t.get("action") == "buy"),
            "sell_trades": sum(1 for t in self.trades if t.get("action") == "sell"),
            "winning_trades": winning,
            "losing_trades": losing,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "initial_balance": self.initial_balance,
            "current_estimate": current_estimate,
            "daily_pnl": daily_pnl,
            "weekly_pnl": weekly_pnl,
            "monthly_pnl": monthly_pnl,
            "equity_curve": self.equity_curve,
            "best_trade": best_trade,
            "worst_trade": worst_trade,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_dd,
        }


# Singleton instance
_agent: Optional[RLTradingAgent] = None


def get_agent(
    symbol: str = "BTC/USD",
    mode: str = "paper",
    checkpoint_path: Optional[str] = None,
) -> RLTradingAgent:
    """Get or create the global agent instance."""
    global _agent

    if _agent is None:
        _agent = RLTradingAgent(
            symbol=symbol,
            mode=mode,
            checkpoint_path=checkpoint_path,
        )
        if checkpoint_path:
            _agent.load_model(checkpoint_path)

    return _agent


def reset_agent():
    """Reset the global agent."""
    global _agent
    _agent = None
