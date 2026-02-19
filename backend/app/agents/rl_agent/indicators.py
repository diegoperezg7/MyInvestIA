"""
Advanced Technical Indicators for Trading Agent.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional


class TechnicalIndicators:
    """Calculate technical indicators for trading signals."""

    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average."""
        return data.rolling(window=period).mean()

    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average."""
        return data.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index."""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def macd(
        data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD - Moving Average Convergence Divergence."""
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def bollinger_bands(
        data: pd.Series, period: int = 20, std_dev: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands."""
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return sma, upper_band, lower_band

    @staticmethod
    def atr(
        high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
    ) -> pd.Series:
        """Average True Range."""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    @staticmethod
    def stochastic(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
        smooth_k: int = 3,
        smooth_d: int = 3,
    ) -> Tuple[pd.Series, pd.Series]:
        """Stochastic Oscillator."""
        lowest_low = low.rolling(window=period).min()
        highest_high = high.rolling(window=period).max()
        k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        k_smooth = k.rolling(window=smooth_k).mean()
        d = k_smooth.rolling(window=smooth_d).mean()
        return k_smooth, d

    @staticmethod
    def adx(
        high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
    ) -> pd.Series:
        """Average Directional Index."""
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = TechnicalIndicators.atr(high, low, close, period)

        plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / tr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return adx

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """On-Balance Volume."""
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        return obv

    @staticmethod
    def vwap(
        high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
    ) -> pd.Series:
        """Volume Weighted Average Price."""
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        return vwap

    @staticmethod
    def cci(
        high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20
    ) -> pd.Series:
        """Commodity Channel Index."""
        typical_price = (high + low + close) / 3
        sma = typical_price.rolling(window=period).mean()
        mean_deviation = typical_price.rolling(window=period).apply(
            lambda x: np.mean(np.abs(x - x.mean()))
        )
        cci = (typical_price - sma) / (0.015 * mean_deviation)
        return cci

    @staticmethod
    def williams_r(
        high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
    ) -> pd.Series:
        """Williams %R."""
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        williams_r = -100 * ((highest_high - close) / (highest_high - lowest_low))
        return williams_r

    @staticmethod
    def momentum(data: pd.Series, period: int = 10) -> pd.Series:
        """Momentum."""
        return data.diff(period)

    @staticmethod
    def roc(data: pd.Series, period: int = 10) -> pd.Series:
        """Rate of Change."""
        return 100 * (data.diff(period) / data.shift(period))


class SignalGenerator:
    """Generate trading signals based on multiple indicators."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.indicators = TechnicalIndicators()

    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all indicators and add to DataFrame."""
        result = df.copy()

        close = df["Close"]
        high = df.get("High", close)
        low = df.get("Low", close)
        volume = df.get("Volume", pd.Series([1] * len(close)))

        # Moving Averages
        result["sma_20"] = self.indicators.sma(close, 20)
        result["sma_50"] = self.indicators.sma(close, 50)
        result["sma_200"] = self.indicators.sma(close, 200)
        result["ema_12"] = self.indicators.ema(close, 12)
        result["ema_26"] = self.indicators.ema(close, 26)

        # RSI
        result["rsi_14"] = self.indicators.rsi(close, 14)
        result["rsi_7"] = self.indicators.rsi(close, 7)

        # MACD
        macd, signal, hist = self.indicators.macd(close)
        result["macd"] = macd
        result["macd_signal"] = signal
        result["macd_histogram"] = hist

        # Bollinger Bands
        bb_mid, bb_upper, bb_lower = self.indicators.bollinger_bands(close)
        result["bb_mid"] = bb_mid
        result["bb_upper"] = bb_upper
        result["bb_lower"] = bb_lower
        result["bb_width"] = (bb_upper - bb_lower) / bb_mid
        result["bb_position"] = (close - bb_lower) / (bb_upper - bb_lower)

        # ATR
        result["atr_14"] = self.indicators.atr(high, low, close, 14)

        # Stochastic
        stoch_k, stoch_d = self.indicators.stochastic(high, low, close)
        result["stoch_k"] = stoch_k
        result["stoch_d"] = stoch_d

        # ADX
        result["adx_14"] = self.indicators.adx(high, low, close, 14)

        # OBV
        result["obv"] = self.indicators.obv(close, volume)

        # VWAP
        result["vwap"] = self.indicators.vwap(high, low, close, volume)

        # CCI
        result["cci_20"] = self.indicators.cci(high, low, close, 20)

        # Williams %R
        result["williams_r_14"] = self.indicators.williams_r(high, low, close, 14)

        # Momentum
        result["momentum_10"] = self.indicators.momentum(close, 10)
        result["roc_10"] = self.indicators.roc(close, 10)

        # Returns
        result["returns"] = close.pct_change()
        result["log_returns"] = np.log(close / close.shift(1))

        # Volatility
        result["volatility_20"] = close.rolling(20).std()

        return result

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals based on indicators."""
        signals = self.calculate_all(df)

        # Initialize signal column
        signals["signal"] = 0  # 0 = hold, 1 = buy, -1 = sell
        signals["signal_strength"] = 0.0

        # RSI signals
        rsi = signals["rsi_14"]
        signals.loc[rsi < 30, "signal"] = 1  # Oversold -> Buy
        signals.loc[rsi > 70, "signal"] = -1  # Overbought -> Sell

        # MACD signals
        macd = signals["macd"]
        macd_signal = signals["macd_signal"]
        macd_cross = (macd > macd_signal) & (macd.shift(1) <= macd_signal.shift(1))
        macd_cross_down = (macd < macd_signal) & (macd.shift(1) >= macd_signal.shift(1))

        signals.loc[macd_cross, "signal"] = 1
        signals.loc[macd_cross_down, "signal"] = -1

        # Bollinger Bands signals
        bb_position = signals["bb_position"]
        signals.loc[bb_position < 0.1, "signal"] = 1  # Near lower band -> Buy
        signals.loc[bb_position > 0.9, "signal"] = -1  # Near upper band -> Sell

        # Stochastic signals
        stoch_k = signals["stoch_k"]
        stoch_d = signals["stoch_d"]
        signals.loc[(stoch_k < 20) & (stoch_k > stoch_d), "signal"] = 1
        signals.loc[(stoch_k > 80) & (stoch_k < stoch_d), "signal"] = -1

        # Calculate signal strength (0-1)
        rsi_strength = 1 - (rsi / 100).abs()
        signals["signal_strength"] = rsi_strength

        return signals

    def get_latest_signal(self, df: pd.DataFrame) -> Dict:
        """Get the latest trading signal."""
        signals = self.generate_signals(df)

        latest = signals.iloc[-1]

        # Determine final signal
        buy_signals = (signals["signal"] == 1).iloc[-5:].sum()
        sell_signals = (signals["signal"] == -1).iloc[-5:].sum()

        if buy_signals >= 3:
            action = "buy"
            confidence = buy_signals / 5
        elif sell_signals >= 3:
            action = "sell"
            confidence = sell_signals / 5
        else:
            action = "hold"
            confidence = 0.3

        return {
            "action": action,
            "confidence": float(confidence),
            "rsi_14": float(latest["rsi_14"]),
            "macd": float(latest["macd"]),
            "macd_signal": float(latest["macd_signal"]),
            "macd_histogram": float(latest["macd_histogram"]),
            "bb_position": float(latest["bb_position"]),
            "stoch_k": float(latest["stoch_k"]),
            "stoch_d": float(latest["stoch_d"]),
            "adx_14": float(latest["adx_14"]),
            "atr_14": float(latest["atr_14"]),
            "price": float(latest["Close"]),
            "sma_20": float(latest["sma_20"]),
            "sma_50": float(latest["sma_50"]),
            "trend": "bullish" if latest["Close"] > latest["sma_50"] else "bearish",
            "volatility": float(latest["volatility_20"]),
        }


def calculate_portfolio_metrics(trades: list, initial_balance: float = 10000) -> Dict:
    """Calculate comprehensive portfolio metrics."""
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "total_pnl_pct": 0,
        }

    # Group trades by symbol
    trades_by_symbol = {}
    for trade in trades:
        symbol = trade.get("symbol", "UNKNOWN")
        if symbol not in trades_by_symbol:
            trades_by_symbol[symbol] = []
        trades_by_symbol[symbol].append(trade)

    # Calculate metrics
    total_pnl = 0
    winning_trades = 0
    losing_trades = 0
    total_fees = 0

    for symbol, symbol_trades in trades_by_symbol.items():
        # Match buys and sells
        buys = [t for t in symbol_trades if t.get("action") == "buy"]
        sells = [t for t in symbol_trades if t.get("action") == "sell"]

        for buy in buys:
            for sell in sells:
                if sell.get("timestamp", "") > buy.get("timestamp", ""):
                    pnl = (sell.get("price", 0) - buy.get("price", 0)) * buy.get(
                        "quantity", 0
                    )
                    total_pnl += pnl

                    fees = buy.get("value", 0) * 0.001 + sell.get("value", 0) * 0.001
                    total_fees += fees

                    if pnl > 0:
                        winning_trades += 1
                    else:
                        losing_trades += 1
                    break

    total_trades = winning_trades + losing_trades

    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": winning_trades / total_trades if total_trades > 0 else 0,
        "total_pnl": total_pnl,
        "total_pnl_pct": (total_pnl / initial_balance) * 100,
        "total_fees": total_fees,
        "net_pnl": total_pnl - total_fees,
        "net_pnl_pct": ((total_pnl - total_fees) / initial_balance) * 100,
    }
