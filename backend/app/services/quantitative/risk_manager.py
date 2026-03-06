from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import pandas as pd
import numpy as np
import logging


@dataclass
class RiskMetrics:
    portfolio_value: float
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    max_drawdown: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    beta: float = 0.0
    alpha: float = 0.0


@dataclass
class RiskLimits:
    max_position_size: float = 0.1
    max_portfolio_volatility: float = 0.30
    max_drawdown: float = 0.20
    max_leverage: float = 1.0
    max_correlation: float = 0.7
    min_diversification: float = 10


class RiskManager:
    def __init__(self, risk_limits: Optional[RiskLimits] = None):
        self.risk_limits = risk_limits or RiskLimits()
        self.logger = logging.getLogger("risk_manager")

    def calculate_var(self, returns: pd.Series, confidence: float = 0.95) -> float:
        if returns.empty:
            return 0.0
        return np.percentile(returns, (1 - confidence) * 100)

    def calculate_cvar(self, returns: pd.Series, confidence: float = 0.95) -> float:
        if returns.empty:
            return 0.0
        var = self.calculate_var(returns, confidence)
        return returns[returns <= var].mean()

    def calculate_max_drawdown(self, equity_curve: pd.Series) -> float:
        if equity_curve.empty:
            return 0.0
        peak = equity_curve.expanding().max()
        drawdown = (equity_curve - peak) / peak
        return abs(drawdown.min())

    def calculate_sharpe_ratio(
        self, returns: pd.Series, risk_free_rate: float = 0.02
    ) -> float:
        if returns.empty or returns.std() == 0:
            return 0.0
        excess_return = returns.mean() * 252 - risk_free_rate
        return excess_return / (returns.std() * np.sqrt(252))

    def calculate_sortino_ratio(
        self, returns: pd.Series, risk_free_rate: float = 0.02
    ) -> float:
        if returns.empty:
            return 0.0

        downside_returns = returns[returns < 0]
        if downside_returns.empty or downside_returns.std() == 0:
            return 0.0

        excess_return = returns.mean() * 252 - risk_free_rate
        downside_std = downside_returns.std() * np.sqrt(252)

        return excess_return / downside_std

    def calculate_portfolio_risk(
        self,
        positions: Dict[str, float],
        returns_data: pd.DataFrame,
        current_prices: Dict[str, float],
    ) -> RiskMetrics:
        if not positions or returns_data.empty:
            return RiskMetrics(
                portfolio_value=0.0,
                var_95=0.0,
                var_99=0.0,
                cvar_95=0.0,
                cvar_99=0.0,
                max_drawdown=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
            )

        portfolio_value = sum(
            pos * current_prices.get(sym, 0) for sym, pos in positions.items()
        )

        portfolio_returns = pd.Series(0.0, index=returns_data.index)
        for symbol, weight in positions.items():
            if symbol in returns_data.columns:
                portfolio_returns += returns_data[symbol] * weight

        var_95 = abs(self.calculate_var(portfolio_returns, 0.95))
        var_99 = abs(self.calculate_var(portfolio_returns, 0.99))
        cvar_95 = abs(self.calculate_cvar(portfolio_returns, 0.95))
        cvar_99 = abs(self.calculate_cvar(portfolio_returns, 0.99))

        volatility = portfolio_returns.std() * np.sqrt(252)
        sharpe = self.calculate_sharpe_ratio(portfolio_returns)
        sortino = self.calculate_sortino_ratio(portfolio_returns)

        equity_curve = (1 + portfolio_returns).cumprod()
        max_dd = self.calculate_max_drawdown(equity_curve)

        return RiskMetrics(
            portfolio_value=portfolio_value,
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            max_drawdown=max_dd,
            volatility=volatility,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
        )

    def check_position_limits(
        self, symbol: str, position_value: float, portfolio_value: float
    ) -> bool:
        if portfolio_value <= 0:
            return False

        position_ratio = position_value / portfolio_value

        if position_ratio > self.risk_limits.max_position_size:
            self.logger.warning(
                f"Position size limit exceeded for {symbol}: {position_ratio:.2%} > {self.risk_limits.max_position_size:.2%}"
            )
            return False

        return True

    def check_volatility_limits(self, volatility: float) -> bool:
        if volatility > self.risk_limits.max_portfolio_volatility:
            self.logger.warning(
                f"Portfolio volatility limit exceeded: {volatility:.2%} > {self.risk_limits.max_portfolio_volatility:.2%}"
            )
            return False
        return True

    def check_drawdown_limits(self, current_drawdown: float) -> bool:
        if current_drawdown > self.risk_limits.max_drawdown:
            self.logger.warning(
                f"Drawdown limit exceeded: {current_drawdown:.2%} > {self.risk_limits.max_drawdown:.2%}"
            )
            return False
        return True

    def calculate_position_size(
        self,
        symbol: str,
        capital: float,
        volatility: float,
        target_volatility: float = 0.15,
        risk_factor: float = 1.0,
    ) -> float:
        if volatility <= 0:
            return capital * self.risk_limits.max_position_size

        position_size = (capital * target_volatility * risk_factor) / volatility

        max_size = capital * self.risk_limits.max_position_size

        return min(position_size, max_size)

    def calculate_kelly_criterion(
        self, win_rate: float, avg_win: float, avg_loss: float
    ) -> float:
        if avg_loss <= 0:
            return 0.0

        win_loss_ratio = avg_win / avg_loss
        kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio

        return max(0, min(kelly, 0.25))

    def diversify_positions(
        self, positions: Dict[str, float], target_count: int = 10
    ) -> Dict[str, float]:
        if len(positions) <= target_count:
            return positions

        sorted_positions = sorted(positions.items(), key=lambda x: x[1], reverse=True)

        return dict(sorted_positions[:target_count])
