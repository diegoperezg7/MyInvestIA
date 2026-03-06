import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, field


@dataclass
class Trade:
    timestamp: datetime
    symbol: str
    side: str
    quantity: float
    price: float
    order_id: str
    status: str = "filled"
    commission: float = 0.0


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


@dataclass
class BacktestResult:
    initial_capital: float
    final_value: float
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    avg_trade_return: float
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)
    trades: List[Trade] = field(default_factory=list)
    positions: Dict[str, Position] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)


class BacktestEngine:
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.001,
        slippage: float = 0.0005,
        leverage: float = 1.0,
    ):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.leverage = leverage
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)

    def reset(self):
        self.current_capital = self.initial_capital
        self.positions.clear()
        self.trades.clear()
        self.equity_curve.clear()

    def run_backtest(
        self,
        price_data: pd.DataFrame,
        signals: Dict[str, List[Dict[str, Any]]],
        initial_capital: Optional[float] = None,
    ) -> BacktestResult:
        self.reset()

        if initial_capital:
            self.initial_capital = initial_capital
            self.current_capital = initial_capital

        price_data = price_data.sort_values("timestamp")

        timestamps = (
            price_data["timestamp"].unique()
            if "timestamp" in price_data.columns
            else price_data.index.unique()
        )

        for ts in timestamps:
            if isinstance(ts, pd.Timestamp):
                ts = ts.to_pydatetime()

            current_prices = (
                price_data[price_data["timestamp"] == ts]
                if "timestamp" in price_data.columns
                else price_data.loc[ts:ts]
                if isinstance(ts, str)
                else price_data.iloc[ts : ts + 1]
            )

            if current_prices.empty:
                continue

            for _, row in current_prices.iterrows():
                symbol = row.get("symbol", "")
                if not symbol:
                    continue

                price = row.get("close", row.get("price", 0))
                if price <= 0:
                    continue

                if symbol in signals:
                    for signal in signals[symbol]:
                        if signal.get("timestamp") == ts or not signal.get("timestamp"):
                            action = signal.get("action", "")
                            if action == "BUY":
                                self._execute_buy(
                                    symbol, price, ts, signal.get("quantity")
                                )
                            elif action == "SELL":
                                self._execute_sell(
                                    symbol, price, ts, signal.get("quantity")
                                )

            self._update_equity_curve(ts, current_prices)

        return self._calculate_results()

    def _execute_buy(
        self,
        symbol: str,
        price: float,
        timestamp: datetime,
        quantity: Optional[float] = None,
    ):
        execution_price = price * (1 + self.slippage)
        commission = execution_price * self.commission_rate

        if quantity is None:
            available_capital = self.current_capital * self.leverage
            quantity = (available_capital - commission) / execution_price

        total_cost = execution_price * quantity + commission

        if total_cost > self.current_capital * self.leverage:
            quantity = (
                self.current_capital * self.leverage - commission
            ) / execution_price
            total_cost = execution_price * quantity + commission

        if quantity <= 0:
            return

        self.current_capital -= total_cost

        if symbol in self.positions:
            pos = self.positions[symbol]
            total_quantity = pos.quantity + quantity
            total_cost_basis = pos.quantity * pos.avg_price + quantity * execution_price
            pos.avg_price = total_cost_basis / total_quantity
            pos.quantity = total_quantity
        else:
            self.positions[symbol] = Position(
                symbol=symbol, quantity=quantity, avg_price=execution_price
            )

        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            side="buy",
            quantity=quantity,
            price=execution_price,
            order_id=f"order_{len(self.trades)}",
            commission=commission,
        )
        self.trades.append(trade)

    def _execute_sell(
        self,
        symbol: str,
        price: float,
        timestamp: datetime,
        quantity: Optional[float] = None,
    ):
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        execution_price = price * (1 - self.slippage)
        commission = execution_price * self.commission_rate

        if quantity is None:
            quantity = pos.quantity

        quantity = min(quantity, pos.quantity)

        proceeds = execution_price * quantity - commission
        self.current_capital += proceeds

        pnl = (execution_price - pos.avg_price) * quantity - commission
        pos.realized_pnl += pnl

        pos.quantity -= quantity

        if pos.quantity <= 0:
            del self.positions[symbol]

        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            side="sell",
            quantity=quantity,
            price=execution_price,
            order_id=f"order_{len(self.trades)}",
            commission=commission,
        )
        self.trades.append(trade)

    def _update_equity_curve(self, timestamp: datetime, price_data: pd.DataFrame):
        total_value = self.current_capital

        for symbol, pos in self.positions.items():
            current_price_row = price_data[price_data["symbol"] == symbol]
            if not current_price_row.empty:
                current_price = current_price_row.iloc[0].get(
                    "close", current_price_row.iloc[0].get("price", pos.avg_price)
                )
            else:
                current_price = pos.avg_price

            pos.unrealized_pnl = (current_price - pos.avg_price) * pos.quantity
            total_value += pos.quantity * current_price

        self.equity_curve.append(
            {
                "timestamp": timestamp,
                "total_value": total_value,
                "cash": self.current_capital,
                "positions_value": total_value - self.current_capital,
                "unrealized_pnl": sum(
                    p.unrealized_pnl for p in self.positions.values()
                ),
            }
        )

    def _calculate_results(self) -> BacktestResult:
        if not self.equity_curve:
            return BacktestResult(
                initial_capital=self.initial_capital,
                final_value=self.initial_capital,
                total_return=0.0,
                annualized_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown=0.0,
                calmar_ratio=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                profit_factor=0.0,
                avg_trade_return=0.0,
            )

        equity_df = pd.DataFrame(self.equity_curve)
        if "timestamp" in equity_df.columns:
            equity_df.set_index("timestamp", inplace=True)

        equity_df["returns"] = equity_df["total_value"].pct_change()

        total_return = (
            equity_df["total_value"].iloc[-1] - self.initial_capital
        ) / self.initial_capital

        total_days = (
            (equity_df.index[-1] - equity_df.index[0]).days if len(equity_df) > 1 else 1
        )
        years = max(total_days / 365, 1 / 365)
        annualized_return = (1 + total_return) ** (1 / years) - 1

        returns = equity_df["returns"].dropna()
        volatility = returns.std() * np.sqrt(252) if len(returns) > 0 else 0

        risk_free_rate = 0.02
        sharpe_ratio = (
            (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0
        )

        downside_returns = returns[returns < 0]
        downside_std = (
            downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 1
        )
        sortino_ratio = (
            (annualized_return - risk_free_rate) / downside_std
            if downside_std > 0
            else 0
        )

        peak = equity_df["total_value"].expanding().max()
        drawdown = (equity_df["total_value"] - peak) / peak
        max_drawdown = drawdown.min()

        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0

        total_trades = len(self.trades)
        buy_trades = [t for t in self.trades if t.side == "buy"]
        sell_trades = [t for t in self.trades if t.side == "sell"]

        trade_returns = []
        winning_trades = 0
        losing_trades = 0
        total_profit = 0
        total_loss = 0

        for i in range(0, len(sell_trades), 2):
            if i + 1 < len(buy_trades):
                buy_trade = (
                    buy_trades[i // 2] if i // 2 < len(buy_trades) else buy_trades[-1]
                )
                sell_trade = sell_trades[i]
                if sell_trade.symbol == buy_trade.symbol:
                    trade_return = (
                        sell_trade.price - buy_trade.price
                    ) / buy_trade.price
                    trade_returns.append(trade_return)
                    if trade_return > 0:
                        winning_trades += 1
                        total_profit += trade_return
                    else:
                        losing_trades += 1
                        total_loss += abs(trade_return)

        win_rate = (
            winning_trades / (winning_trades + losing_trades)
            if (winning_trades + losing_trades) > 0
            else 0
        )
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        avg_trade_return = np.mean(trade_returns) if trade_returns else 0

        return BacktestResult(
            initial_capital=self.initial_capital,
            final_value=equity_df["total_value"].iloc[-1],
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            calmar_ratio=calmar_ratio,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_trade_return=avg_trade_return,
            equity_curve=equity_df,
            trades=self.trades,
            positions=self.positions,
            metrics={
                "total_days": total_days,
                "avg_daily_return": returns.mean() if len(returns) > 0 else 0,
                "best_trade": max(trade_returns) if trade_returns else 0,
                "worst_trade": min(trade_returns) if trade_returns else 0,
            },
        )

    def get_current_positions(self) -> Dict[str, Position]:
        return self.positions.copy()

    def get_trade_history(self) -> List[Trade]:
        return self.trades.copy()
