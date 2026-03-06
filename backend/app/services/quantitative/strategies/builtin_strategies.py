from typing import Dict, List, Any
import pandas as pd
import numpy as np
from datetime import datetime
from .strategy_base import StrategyBase, StrategyResult


class MomentumStrategy(StrategyBase):
    def __init__(self):
        super().__init__(
            name="MomentumStrategy",
            description="Select stocks with highest momentum",
        )

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "lookback_period": {"type": "int", "default": 60, "min": 20, "max": 252},
            "top_n": {"type": "int", "default": 20, "min": 5, "max": 100},
            "min_momentum": {"type": "float", "default": 5.0, "min": 0.0, "max": 50.0},
            "rebalance_frequency": {
                "type": "str",
                "default": "monthly",
                "options": ["daily", "weekly", "monthly", "quarterly"],
            },
        }

    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        schema = self.get_parameter_schema()
        for param_name, param_info in schema.items():
            if param_name in parameters:
                value = parameters[param_name]
                if param_info["type"] == "int":
                    if (
                        not isinstance(value, int)
                        or value < param_info["min"]
                        or value > param_info["max"]
                    ):
                        return False
                elif param_info["type"] == "float":
                    if (
                        not isinstance(value, (int, float))
                        or value < param_info["min"]
                        or value > param_info["max"]
                    ):
                        return False
                elif param_info["type"] == "str":
                    if value not in param_info["options"]:
                        return False
        return True

    def generate_signals(
        self,
        factor_data: pd.DataFrame,
        price_data: pd.DataFrame,
        **kwargs,
    ) -> StrategyResult:
        lookback_period = self.parameters.get("lookback_period", 60)
        top_n = self.parameters.get("top_n", 20)
        min_momentum = self.parameters.get("min_momentum", 5.0)

        momentum_col = f"momentum_{lookback_period}d"

        if momentum_col not in factor_data.columns:
            if "close" in price_data.columns and "symbol" in price_data.columns:
                factor_data = self._calculate_momentum(
                    price_data, lookback_period, factor_data
                )

        if momentum_col in factor_data.columns:
            filtered = factor_data[factor_data[momentum_col] >= min_momentum].copy()
            filtered = filtered.sort_values(momentum_col, ascending=False).head(top_n)

            if "symbol" in filtered.columns:
                selected_stocks = filtered["symbol"].unique().tolist()[:top_n]
            elif "symbol" in factor_data.columns:
                selected_stocks = factor_data["symbol"].unique().tolist()[:top_n]
            else:
                selected_stocks = []
        else:
            if "symbol" in factor_data.columns:
                selected_stocks = factor_data["symbol"].unique().tolist()[:top_n]
            else:
                selected_stocks = []

        if selected_stocks:
            weight = 1.0 / len(selected_stocks)
            weights = {stock: weight for stock in selected_stocks}
        else:
            weights = {}

        signals = {stock: "BUY" for stock in selected_stocks}

        return StrategyResult(
            strategy_name=self.name,
            selected_stocks=selected_stocks,
            weights=weights,
            parameters=self.parameters,
            execution_time=datetime.now(),
            performance_metrics={"num_stocks": len(selected_stocks)},
            signals=signals,
            metadata={"lookback_period": lookback_period},
        )

    def _calculate_momentum(
        self, price_data: pd.DataFrame, lookback: int, factor_data: pd.DataFrame
    ) -> pd.DataFrame:
        if "close" in price_data.columns and "symbol" in price_data.columns:
            for symbol in price_data["symbol"].unique():
                symbol_data = price_data[price_data["symbol"] == symbol].sort_index()
                if len(symbol_data) >= lookback:
                    momentum = (
                        (
                            symbol_data["close"].iloc[-1]
                            - symbol_data["close"].iloc[-lookback]
                        )
                        / symbol_data["close"].iloc[-lookback]
                        * 100
                    )
                    momentum_col = f"momentum_{lookback}d"
                    if momentum_col not in factor_data.columns:
                        factor_data[momentum_col] = np.nan
                    factor_data.loc[price_data["symbol"] == symbol, momentum_col] = (
                        momentum
                    )
        return factor_data


class ValueStrategy(StrategyBase):
    def __init__(self):
        super().__init__(
            name="ValueStrategy",
            description="Select stocks with low valuation metrics",
        )

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "max_pe": {"type": "float", "default": 15.0, "min": 5.0, "max": 50.0},
            "max_pb": {"type": "float", "default": 2.0, "min": 0.5, "max": 10.0},
            "min_dividend_yield": {
                "type": "float",
                "default": 2.0,
                "min": 0.0,
                "max": 10.0,
            },
            "top_n": {"type": "int", "default": 30, "min": 5, "max": 100},
        }

    def generate_signals(
        self,
        factor_data: pd.DataFrame,
        price_data: pd.DataFrame,
        **kwargs,
    ) -> StrategyResult:
        max_pe = self.parameters.get("max_pe", 15.0)
        max_pb = self.parameters.get("max_pb", 2.0)
        top_n = self.parameters.get("top_n", 30)

        selected_stocks = []

        pe_col = "pe_ratio" if "pe_ratio" in factor_data.columns else "pe"

        if pe_col in factor_data.columns:
            filtered = factor_data[factor_data[pe_col] <= max_pe].copy()
            if "pb_ratio" in factor_data.columns or "pb" in factor_data.columns:
                pb_col = "pb_ratio" if "pb_ratio" in factor_data.columns else "pb"
                filtered = filtered[filtered[pb_col] <= max_pb]
            filtered = filtered.sort_values(pe_col).head(top_n)
            selected_stocks = (
                filtered.index.tolist() if hasattr(filtered, "index") else []
            )

        if selected_stocks:
            weight = 1.0 / len(selected_stocks)
            weights = {stock: weight for stock in selected_stocks}
        else:
            weights = {}

        signals = {stock: "BUY" for stock in selected_stocks}

        return StrategyResult(
            strategy_name=self.name,
            selected_stocks=selected_stocks,
            weights=weights,
            parameters=self.parameters,
            execution_time=datetime.now(),
            performance_metrics={"num_stocks": len(selected_stocks)},
            signals=signals,
            metadata={},
        )


class QualityGrowthStrategy(StrategyBase):
    def __init__(self):
        super().__init__(
            name="QualityGrowthStrategy",
            description="Select high-quality growth stocks",
        )

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "min_roe": {"type": "float", "default": 15.0, "min": 5.0, "max": 50.0},
            "max_debt_equity": {
                "type": "float",
                "default": 0.5,
                "min": 0.0,
                "max": 2.0,
            },
            "min_current_ratio": {
                "type": "float",
                "default": 1.5,
                "min": 0.5,
                "max": 5.0,
            },
            "min_growth": {"type": "float", "default": 10.0, "min": 0.0, "max": 50.0},
            "top_n": {"type": "int", "default": 25, "min": 5, "max": 100},
        }

    def generate_signals(
        self,
        factor_data: pd.DataFrame,
        price_data: pd.DataFrame,
        **kwargs,
    ) -> StrategyResult:
        min_roe = self.parameters.get("min_roe", 15.0)
        max_debt_equity = self.parameters.get("max_debt_equity", 0.5)
        top_n = self.parameters.get("top_n", 25)

        selected_stocks = []

        roe_col = "roe" if "roe" in factor_data.columns else "return_on_equity"

        if roe_col in factor_data.columns:
            filtered = factor_data[factor_data[roe_col] >= min_roe].copy()

            debt_col = (
                "debt_to_equity"
                if "debt_to_equity" in factor_data.columns
                else "debt_equity"
            )
            if debt_col in factor_data.columns:
                filtered = filtered[filtered[debt_col] <= max_debt_equity]

            filtered = filtered.sort_values(roe_col, ascending=False).head(top_n)
            selected_stocks = (
                filtered.index.tolist() if hasattr(filtered, "index") else []
            )

        if selected_stocks:
            weight = 1.0 / len(selected_stocks)
            weights = {stock: weight for stock in selected_stocks}
        else:
            weights = {}

        signals = {stock: "BUY" for stock in selected_stocks}

        return StrategyResult(
            strategy_name=self.name,
            selected_stocks=selected_stocks,
            weights=weights,
            parameters=self.parameters,
            execution_time=datetime.now(),
            performance_metrics={"num_stocks": len(selected_stocks)},
            signals=signals,
            metadata={},
        )


class MeanReversionStrategy(StrategyBase):
    def __init__(self):
        super().__init__(
            name="MeanReversionStrategy",
            description="Buy oversold stocks based on technical indicators",
        )

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "rsi_oversold": {
                "type": "float",
                "default": 30.0,
                "min": 20.0,
                "max": 40.0,
            },
            "rsi_overbought": {
                "type": "float",
                "default": 70.0,
                "min": 60.0,
                "max": 80.0,
            },
            "lookback_period": {"type": "int", "default": 20, "min": 10, "max": 50},
            "top_n": {"type": "int", "default": 10, "min": 5, "max": 50},
        }

    def generate_signals(
        self,
        factor_data: pd.DataFrame,
        price_data: pd.DataFrame,
        **kwargs,
    ) -> StrategyResult:
        rsi_oversold = self.parameters.get("rsi_oversold", 30.0)
        top_n = self.parameters.get("top_n", 10)

        selected_stocks = []

        rsi_col = "rsi" if "rsi" in factor_data.columns else "rsi_14"

        if rsi_col in factor_data.columns:
            filtered = factor_data[factor_data[rsi_col] <= rsi_oversold].copy()
            filtered = filtered.sort_values(rsi_col).head(top_n)
            selected_stocks = (
                filtered.index.tolist() if hasattr(filtered, "index") else []
            )
        else:
            if "close" in price_data.columns and "symbol" in price_data.columns:
                price_data = self._calculate_rsi(price_data)
                if "rsi" in price_data.columns:
                    filtered = price_data[price_data["rsi"] <= rsi_oversold].copy()
                    selected_stocks = filtered["symbol"].unique().tolist()[:top_n]

        if selected_stocks:
            weight = 1.0 / len(selected_stocks)
            weights = {stock: weight for stock in selected_stocks}
        else:
            weights = {}

        signals = {stock: "BUY" for stock in selected_stocks}

        return StrategyResult(
            strategy_name=self.name,
            selected_stocks=selected_stocks,
            weights=weights,
            parameters=self.parameters,
            execution_time=datetime.now(),
            performance_metrics={"num_stocks": len(selected_stocks)},
            signals=signals,
            metadata={},
        )

    def _calculate_rsi(
        self, price_data: pd.DataFrame, period: int = 14
    ) -> pd.DataFrame:
        if "close" not in price_data.columns:
            return price_data

        result_dfs = []
        for symbol in price_data["symbol"].unique():
            symbol_data = price_data[price_data["symbol"] == symbol].copy()
            if len(symbol_data) >= period:
                delta = symbol_data["close"].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / loss
                symbol_data["rsi"] = 100 - (100 / (1 + rs))
            else:
                symbol_data["rsi"] = 50
            result_dfs.append(symbol_data)

        return pd.concat(result_dfs) if result_dfs else price_data


class MultiFactorStrategy(StrategyBase):
    def __init__(self):
        super().__init__(
            name="MultiFactorStrategy",
            description="Combine multiple factors with optimized weights",
        )

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "momentum_weight": {
                "type": "float",
                "default": 0.3,
                "min": 0.0,
                "max": 1.0,
            },
            "value_weight": {"type": "float", "default": 0.2, "min": 0.0, "max": 1.0},
            "quality_weight": {"type": "float", "default": 0.2, "min": 0.0, "max": 1.0},
            "volatility_weight": {
                "type": "float",
                "default": 0.15,
                "min": 0.0,
                "max": 1.0,
            },
            "size_weight": {"type": "float", "default": 0.15, "min": 0.0, "max": 1.0},
            "top_n": {"type": "int", "default": 20, "min": 5, "max": 100},
        }

    def generate_signals(
        self,
        factor_data: pd.DataFrame,
        price_data: pd.DataFrame,
        **kwargs,
    ) -> StrategyResult:
        momentum_weight = self.parameters.get("momentum_weight", 0.3)
        value_weight = self.parameters.get("value_weight", 0.2)
        quality_weight = self.parameters.get("quality_weight", 0.2)
        volatility_weight = self.parameters.get("volatility_weight", 0.15)
        size_weight = self.parameters.get("size_weight", 0.15)
        top_n = self.parameters.get("top_n", 20)

        scores = pd.Series(0.0, index=factor_data.index)

        if "momentum_60d" in factor_data.columns:
            momentum_norm = (
                factor_data["momentum_60d"] - factor_data["momentum_60d"].min()
            ) / (
                factor_data["momentum_60d"].max()
                - factor_data["momentum_60d"].min()
                + 1e-10
            )
            scores += momentum_norm * momentum_weight

        pe_col = "pe_ratio" if "pe_ratio" in factor_data.columns else "pe"
        if pe_col in factor_data.columns:
            value_norm = 1 - (factor_data[pe_col] - factor_data[pe_col].min()) / (
                factor_data[pe_col].max() - factor_data[pe_col].min() + 1e-10
            )
            scores += value_norm * value_weight

        roe_col = "roe" if "roe" in factor_data.columns else "return_on_equity"
        if roe_col in factor_data.columns:
            quality_norm = (factor_data[roe_col] - factor_data[roe_col].min()) / (
                factor_data[roe_col].max() - factor_data[roe_col].min() + 1e-10
            )
            scores += quality_norm * quality_weight

        if "volatility" in factor_data.columns:
            vol_norm = 1 - (
                factor_data["volatility"] - factor_data["volatility"].min()
            ) / (
                factor_data["volatility"].max()
                - factor_data["volatility"].min()
                + 1e-10
            )
            scores += vol_norm * volatility_weight

        if "market_cap" in factor_data.columns:
            size_norm = (
                factor_data["market_cap"] - factor_data["market_cap"].min()
            ) / (
                factor_data["market_cap"].max()
                - factor_data["market_cap"].min()
                + 1e-10
            )
            scores += size_norm * size_weight

        top_stocks = scores.nlargest(top_n)
        selected_stocks = top_stocks.index.tolist()

        if selected_stocks:
            total_score = top_stocks.sum()
            weights = {
                stock: score / total_score for stock, score in top_stocks.items()
            }
        else:
            weights = {}

        signals = {stock: "BUY" for stock in selected_stocks}

        return StrategyResult(
            strategy_name=self.name,
            selected_stocks=selected_stocks,
            weights=weights,
            parameters=self.parameters,
            execution_time=datetime.now(),
            performance_metrics={"num_stocks": len(selected_stocks)},
            signals=signals,
            metadata={
                "factor_weights": {
                    "momentum": momentum_weight,
                    "value": value_weight,
                    "quality": quality_weight,
                    "volatility": volatility_weight,
                    "size": size_weight,
                }
            },
        )


class MeanVarianceStrategy(StrategyBase):
    def __init__(self):
        super().__init__(
            name="MeanVarianceStrategy",
            description="Mean-variance optimization portfolio",
        )

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "risk_aversion": {"type": "float", "default": 1.0, "min": 0.1, "max": 10.0},
            "top_n": {"type": "int", "default": 20, "min": 5, "max": 50},
        }

    def generate_signals(
        self,
        factor_data: pd.DataFrame,
        price_data: pd.DataFrame,
        **kwargs,
    ) -> StrategyResult:
        risk_aversion = self.parameters.get("risk_aversion", 1.0)
        top_n = self.parameters.get("top_n", 20)

        selected_stocks = (
            factor_data.head(top_n).index.tolist() if len(factor_data) > 0 else []
        )

        if selected_stocks:
            weights = {stock: 1.0 / len(selected_stocks) for stock in selected_stocks}
        else:
            weights = {}

        signals = {stock: "BUY" for stock in selected_stocks}

        return StrategyResult(
            strategy_name=self.name,
            selected_stocks=selected_stocks,
            weights=weights,
            parameters=self.parameters,
            execution_time=datetime.now(),
            performance_metrics={"num_stocks": len(selected_stocks)},
            signals=signals,
            metadata={"risk_aversion": risk_aversion},
        )


STRATEGY_REGISTRY = {
    "momentum": MomentumStrategy,
    "value": ValueStrategy,
    "quality_growth": QualityGrowthStrategy,
    "mean_reversion": MeanReversionStrategy,
    "multi_factor": MultiFactorStrategy,
    "mean_variance": MeanVarianceStrategy,
}


def get_strategy(strategy_name: str) -> StrategyBase:
    strategy_class = STRATEGY_REGISTRY.get(strategy_name.lower())
    if not strategy_class:
        raise ValueError(f"Unknown strategy: {strategy_name}")
    return strategy_class()


def list_strategies() -> List[str]:
    return list(STRATEGY_REGISTRY.keys())
