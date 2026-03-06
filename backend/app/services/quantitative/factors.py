import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging


class FactorCalculator:
    def __init__(self):
        self.logger = logging.getLogger("factor_calculator")

    def calculate_momentum(
        self, prices: pd.DataFrame, periods: List[int] = [20, 60, 120]
    ) -> pd.DataFrame:
        result = prices.copy()

        for period in periods:
            if "close" in result.columns:
                result[f"momentum_{period}d"] = (
                    (result["close"] - result["close"].shift(period))
                    / result["close"].shift(period)
                    * 100
                )

                result[f"returns_{period}d"] = result["close"].pct_change(period) * 100

        return result

    def calculate_volatility(
        self, prices: pd.DataFrame, windows: List[int] = [20, 60]
    ) -> pd.DataFrame:
        result = prices.copy()

        if "returns" in result.columns:
            returns = result["returns"]
        elif "close" in result.columns:
            returns = result["close"].pct_change()
        else:
            return result

        for window in windows:
            result[f"volatility_{window}d"] = (
                returns.rolling(window=window).std() * np.sqrt(252) * 100
            )
            result[f"variance_{window}d"] = returns.rolling(window=window).var() * 100

        return result

    def calculate_rsi(self, prices: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        result = prices.copy()

        if "close" not in result.columns:
            return result

        delta = result["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        result["rsi"] = 100 - (100 / (1 + rs))

        result["rsi_14"] = result["rsi"]

        return result

    def calculate_macd(
        self,
        prices: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> pd.DataFrame:
        result = prices.copy()

        if "close" not in result.columns:
            return result

        ema_fast = result["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = result["close"].ewm(span=slow, adjust=False).mean()

        result["macd"] = ema_fast - ema_slow
        result["macd_signal"] = result["macd"].ewm(span=signal, adjust=False).mean()
        result["macd_histogram"] = result["macd"] - result["macd_signal"]

        return result

    def calculate_bollinger_bands(
        self, prices: pd.DataFrame, period: int = 20, std_dev: float = 2.0
    ) -> pd.DataFrame:
        result = prices.copy()

        if "close" not in result.columns:
            return result

        result["bb_middle"] = result["close"].rolling(window=period).mean()
        rolling_std = result["close"].rolling(window=period).std()

        result["bb_upper"] = result["bb_middle"] + (rolling_std * std_dev)
        result["bb_lower"] = result["bb_middle"] - (rolling_std * std_dev)

        result["bb_width"] = (result["bb_upper"] - result["bb_lower"]) / result[
            "bb_middle"
        ]
        result["bb_position"] = (result["close"] - result["bb_lower"]) / (
            result["bb_upper"] - result["bb_lower"]
        )

        return result

    def calculate_moving_averages(
        self, prices: pd.DataFrame, periods: List[int] = [20, 50, 200]
    ) -> pd.DataFrame:
        result = prices.copy()

        if "close" not in result.columns:
            return result

        for period in periods:
            result[f"sma_{period}"] = result["close"].rolling(window=period).mean()
            result[f"ema_{period}"] = (
                result["close"].ewm(span=period, adjust=False).mean()
            )

        result["sma_50_200_ratio"] = result["sma_50"] / result["sma_200"]

        return result

    def calculate_all_factors(
        self,
        prices: pd.DataFrame,
        fundamental_data: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        result = prices.copy()

        result = self.calculate_momentum(result)
        result = self.calculate_volatility(result)
        result = self.calculate_rsi(result)
        result = self.calculate_macd(result)
        result = self.calculate_bollinger_bands(result)
        result = self.calculate_moving_averages(result)

        if fundamental_data is not None:
            result = pd.concat([result, fundamental_data], axis=1)

        return result


class FactorScreener:
    def __init__(self):
        self.logger = logging.getLogger("factor_screener")
        self.criteria = []
        self.filters = []

    def add_criteria(
        self,
        factor_name: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        weight: float = 1.0,
    ):
        self.criteria.append(
            {
                "factor_name": factor_name,
                "min_value": min_value,
                "max_value": max_value,
                "weight": weight,
            }
        )

    def add_momentum_filter(self, min_momentum: float = 0.0, period: int = 60):
        self.add_criteria(factor_name=f"momentum_{period}d", min_value=min_momentum)

    def add_volatility_filter(self, max_volatility: float = 30.0):
        self.add_criteria(factor_name="volatility_20d", max_value=max_volatility)

    def add_market_cap_filter(self, min_market_cap: float = 1000000000):
        self.add_criteria(factor_name="market_cap", min_value=min_market_cap)

    def screen_stocks(self, factor_data: pd.DataFrame) -> pd.DataFrame:
        if factor_data.empty:
            return pd.DataFrame()

        filtered = factor_data.copy()

        for criterion in self.criteria:
            factor = criterion["factor_name"]
            if factor not in filtered.columns:
                continue

            if criterion["min_value"] is not None:
                filtered = filtered[filtered[factor] >= criterion["min_value"]]

            if criterion["max_value"] is not None:
                filtered = filtered[filtered[factor] <= criterion["max_value"]]

        return filtered

    def rank_stocks(
        self, factor_data: pd.DataFrame, weights: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        if factor_data.empty:
            return pd.DataFrame()

        ranked = factor_data.copy()

        if weights is None:
            weights = {c["factor_name"]: c["weight"] for c in self.criteria}

        score = pd.Series(0.0, index=ranked.index)

        for factor, weight in weights.items():
            if factor not in ranked.columns:
                continue

            if ranked[factor].std() > 0:
                normalized = (ranked[factor] - ranked[factor].mean()) / ranked[
                    factor
                ].std()
                score += normalized * weight

        ranked["score"] = score
        ranked = ranked.sort_values("score", ascending=False)

        return ranked


class StockSelector:
    def select_stocks(
        self,
        factor_data: pd.DataFrame,
        price_data: pd.DataFrame,
        selection_method: str = "top_n",
        n: int = 20,
        factor_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        if factor_data.empty:
            return {"selected_stocks": [], "weights": {}}

        if selection_method == "top_n" and factor_name:
            if factor_name in factor_data.columns:
                sorted_data = factor_data.sort_values(
                    factor_name, ascending=False
                ).head(n)
            else:
                sorted_data = factor_data.head(n)
        elif selection_method == "equal_weight":
            sorted_data = factor_data.head(n)
        else:
            sorted_data = factor_data.head(n)

        selected = sorted_data.index.tolist() if hasattr(sorted_data, "index") else []

        if not selected and "symbol" in sorted_data.columns:
            selected = sorted_data["symbol"].tolist()[:n]

        weight = 1.0 / len(selected) if selected else 0
        weights = {stock: weight for stock in selected}

        return {
            "selected_stocks": selected,
            "weights": weights,
            "method": selection_method,
        }


class FactorOptimizer:
    def __init__(self):
        self.logger = logging.getLogger("factor_optimizer")

    def optimize_weights(
        self,
        factor_data: pd.DataFrame,
        returns: pd.Series,
        method: str = "ic_weighted",
    ) -> Dict[str, float]:
        if factor_data.empty or returns.empty:
            return {}

        weights = {}

        for col in factor_data.columns:
            if factor_data[col].std() > 0:
                if method == "ic_weighted":
                    ic = factor_data[col].corr(returns)
                    weights[col] = abs(ic) if not np.isnan(ic) else 0
                elif method == "variance_inverse":
                    weights[col] = 1.0 / (factor_data[col].var() + 1e-10)
                else:
                    weights[col] = 1.0

        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        return weights
