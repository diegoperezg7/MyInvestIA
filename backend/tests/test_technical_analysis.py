"""Tests for technical analysis indicators.

Uses deterministic price data to validate indicator calculations.
"""

import pytest

from app.services.technical_analysis import (
    bollinger_bands,
    compute_all_indicators,
    ema,
    macd,
    rsi,
    sma,
)


# --- Test data: 50 days of synthetic prices ---
PRICES = [
    100.0, 101.5, 103.0, 102.0, 104.0, 105.5, 104.0, 106.0, 107.5, 108.0,
    107.0, 109.0, 110.5, 109.0, 111.0, 112.5, 111.0, 113.0, 114.5, 115.0,
    114.0, 116.0, 117.5, 116.0, 118.0, 119.5, 118.0, 120.0, 121.5, 122.0,
    121.0, 123.0, 124.5, 123.0, 125.0, 126.5, 125.0, 127.0, 128.5, 129.0,
    128.0, 130.0, 131.5, 130.0, 132.0, 133.5, 132.0, 134.0, 135.5, 136.0,
]


class TestSMA:
    def test_basic_sma(self):
        values = sma([10, 20, 30, 40, 50], period=3)
        assert values[0] is None
        assert values[1] is None
        assert values[2] == pytest.approx(20.0, abs=0.01)
        assert values[3] == pytest.approx(30.0, abs=0.01)
        assert values[4] == pytest.approx(40.0, abs=0.01)

    def test_sma_insufficient_data(self):
        values = sma([10, 20], period=5)
        assert all(v is None for v in values)

    def test_sma_output_length(self):
        values = sma(PRICES, period=20)
        assert len(values) == len(PRICES)
        assert values[18] is None
        assert values[19] is not None


class TestEMA:
    def test_basic_ema(self):
        values = ema([10, 20, 30, 40, 50], period=3)
        assert values[0] is None
        assert values[1] is None
        assert values[2] is not None  # first EMA = SMA seed
        assert values[3] is not None
        assert values[4] is not None

    def test_ema_insufficient_data(self):
        values = ema([10, 20], period=5)
        assert all(v is None for v in values)

    def test_ema_output_length(self):
        values = ema(PRICES, period=12)
        assert len(values) == len(PRICES)


class TestRSI:
    def test_rsi_range(self):
        values = rsi(PRICES, period=14)
        for v in values:
            if v is not None:
                assert 0.0 <= v <= 100.0

    def test_rsi_insufficient_data(self):
        values = rsi([100, 101, 102], period=14)
        assert all(v is None for v in values)

    def test_rsi_output_length(self):
        values = rsi(PRICES, period=14)
        assert len(values) == len(PRICES)

    def test_rsi_uptrend_above_50(self):
        """Consistent uptrend should produce RSI above 50."""
        uptrend = [float(100 + i) for i in range(30)]
        values = rsi(uptrend, period=14)
        last_rsi = values[-1]
        assert last_rsi is not None
        assert last_rsi > 50


class TestMACD:
    def test_macd_output_keys(self):
        result = macd(PRICES)
        assert "macd_line" in result
        assert "signal_line" in result
        assert "histogram" in result

    def test_macd_output_length(self):
        result = macd(PRICES)
        assert len(result["macd_line"]) == len(PRICES)
        assert len(result["signal_line"]) == len(PRICES)
        assert len(result["histogram"]) == len(PRICES)

    def test_macd_insufficient_data(self):
        result = macd([100, 101, 102], slow_period=26)
        assert all(v is None for v in result["macd_line"])


class TestBollingerBands:
    def test_bb_output_keys(self):
        result = bollinger_bands(PRICES, period=20)
        assert "upper" in result
        assert "middle" in result
        assert "lower" in result
        assert "bandwidth" in result

    def test_bb_upper_above_lower(self):
        result = bollinger_bands(PRICES, period=20)
        for u, lo in zip(result["upper"], result["lower"]):
            if u is not None and lo is not None:
                assert u >= lo

    def test_bb_insufficient_data(self):
        result = bollinger_bands([100, 101], period=20)
        assert all(v is None for v in result["upper"])


class TestComputeAllIndicators:
    def test_all_indicators_computed(self):
        result = compute_all_indicators(PRICES)
        assert "rsi" in result
        assert "macd" in result
        assert "sma" in result
        assert "ema" in result
        assert "bollinger_bands" in result
        assert "overall_signal" in result
        assert "signal_counts" in result

    def test_overall_signal_valid(self):
        result = compute_all_indicators(PRICES)
        assert result["overall_signal"] in ("bullish", "bearish", "neutral")

    def test_signal_counts_sum(self):
        result = compute_all_indicators(PRICES)
        counts = result["signal_counts"]
        assert counts["bullish"] + counts["bearish"] + counts["neutral"] == 5

    def test_each_indicator_has_signal(self):
        result = compute_all_indicators(PRICES)
        for key in ("rsi", "macd", "sma", "ema", "bollinger_bands"):
            assert "signal" in result[key]
            assert result[key]["signal"] in ("bullish", "bearish", "neutral")
