from typing import Dict, List, Any, Optional
import pandas as pd
import logging


class QuantitativeTradingService:
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.001,
    ):
        from .strategies.builtin_strategies import (
            get_strategy,
            list_strategies,
            STRATEGY_REGISTRY,
        )
        from .backtest_engine import BacktestEngine
        from .factors import FactorCalculator, FactorScreener
        from .risk_manager import RiskManager, RiskLimits
        from .data_fetchers import get_fetcher

        self.strategies = STRATEGY_REGISTRY
        self.list_strategies = list_strategies
        self.get_strategy = get_strategy
        self.backtest_engine = BacktestEngine(
            initial_capital=initial_capital,
            commission_rate=commission_rate,
        )
        self.factor_calculator = FactorCalculator()
        self.factor_screener = FactorScreener()
        self.risk_manager = RiskManager()
        self.get_fetcher = get_fetcher

        self.logger = logging.getLogger("quantitative_trading")

    def run_strategy(
        self,
        strategy_name: str,
        symbols: List[str],
        start_date: str,
        end_date: str,
        provider: str = "yahoo",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            strategy = self.get_strategy(strategy_name)
            if parameters:
                strategy.set_parameters(parameters)

            fetcher = self.get_fetcher(provider)

            symbol_data = {}
            for symbol in symbols:
                if provider == "yahoo":
                    data = fetcher.get_historical(symbol, period="1y")
                elif provider == "binance":
                    data = fetcher.get_klines(symbol, "1d", 365)
                else:
                    data = fetcher.get_time_series_daily(symbol)

                if not data.empty:
                    data["symbol"] = symbol
                    symbol_data[symbol] = data

            if not symbol_data:
                return {"error": "No data retrieved"}

            selected_stocks = []
            all_weights = {}
            all_signals = {}

            for symbol, data in symbol_data.items():
                factor_data = self.factor_calculator.calculate_all_factors(data)
                result = strategy.generate_signals(factor_data, data)

                if result.selected_stocks:
                    for stock in result.selected_stocks:
                        if stock not in selected_stocks:
                            selected_stocks.append(stock)
                            all_weights[stock] = result.weights.get(stock, 0)
                            all_signals[stock] = result.signals.get(stock, "BUY")

            if not selected_stocks:
                selected_stocks = list(symbol_data.keys())

            return {
                "strategy": strategy_name,
                "signals": all_signals,
                "selected_stocks": selected_stocks,
                "weights": all_weights,
                "metrics": {"num_stocks": len(selected_stocks)},
                "parameters": parameters or {},
            }

        except Exception as e:
            self.logger.error(f"Error running strategy: {e}")
            return {"error": str(e)}

    def run_backtest(
        self,
        strategy_name: str,
        symbols: List[str],
        start_date: str,
        end_date: str,
        initial_capital: Optional[float] = None,
        provider: str = "yahoo",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            strategy = self.get_strategy(strategy_name)
            if parameters:
                strategy.set_parameters(parameters)

            fetcher = self.get_fetcher(provider)

            price_data = pd.DataFrame()
            for symbol in symbols:
                if provider == "yahoo":
                    data = fetcher.get_historical(symbol, period="2y")
                elif provider == "binance":
                    data = fetcher.get_klines(symbol, "1d", 730)
                else:
                    data = fetcher.get_time_series_daily(symbol)

                if not data.empty:
                    data["symbol"] = symbol
                    price_data = pd.concat([price_data, data])

            if price_data.empty:
                return {"error": "No data retrieved"}

            factor_data = self.factor_calculator.calculate_all_factors(price_data)

            result = strategy.generate_signals(factor_data, price_data)

            signals = {}
            for symbol in result.selected_stocks:
                signals[symbol] = [
                    {
                        "action": result.signals.get(symbol, "BUY"),
                        "quantity": result.weights.get(symbol, 0),
                    }
                ]

            backtest_result = self.backtest_engine.run_backtest(
                price_data, signals, initial_capital
            )

            return {
                "strategy": strategy_name,
                "initial_capital": backtest_result.initial_capital,
                "final_value": backtest_result.final_value,
                "total_return": backtest_result.total_return,
                "annualized_return": backtest_result.annualized_return,
                "sharpe_ratio": backtest_result.sharpe_ratio,
                "sortino_ratio": backtest_result.sortino_ratio,
                "max_drawdown": backtest_result.max_drawdown,
                "win_rate": backtest_result.win_rate,
                "total_trades": backtest_result.total_trades,
                "metrics": backtest_result.metrics,
            }

        except Exception as e:
            self.logger.error(f"Error running backtest: {e}")
            return {"error": str(e)}

    def analyze_risk(
        self,
        positions: Dict[str, float],
        returns_data: pd.DataFrame,
        current_prices: Dict[str, float],
    ) -> Dict[str, Any]:
        risk_metrics = self.risk_manager.calculate_portfolio_risk(
            positions, returns_data, current_prices
        )

        return {
            "portfolio_value": risk_metrics.portfolio_value,
            "var_95": risk_metrics.var_95,
            "var_99": risk_metrics.var_99,
            "cvar_95": risk_metrics.cvar_95,
            "cvar_99": risk_metrics.cvar_99,
            "max_drawdown": risk_metrics.max_drawdown,
            "volatility": risk_metrics.volatility,
            "sharpe_ratio": risk_metrics.sharpe_ratio,
            "sortino_ratio": risk_metrics.sortino_ratio,
        }

    def get_available_strategies(self) -> List[Dict[str, Any]]:
        strategies_info = []
        for name in self.list_strategies():
            strategy = self.get_strategy(name)
            strategies_info.append(strategy.get_parameter_info())
        return strategies_info
