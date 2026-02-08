"""Tests for alert scoring service and alerts router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.alert_scorer import score_asset


class TestScoreAsset:
    """Unit tests for the score_asset function with deterministic inputs."""

    def test_no_alerts_for_calm_market(self):
        """Normal conditions should produce no alerts."""
        quote = {"price": 150.0, "change_percent": 1.2, "volume": 50000000}
        indicators = {
            "rsi": {"value": 55.0, "signal": "neutral"},
            "macd": {"macd_line": 0.5, "signal_line": 0.3, "histogram": 0.2, "signal": "bullish"},
            "sma": {"sma_20": 148.0, "sma_50": 145.0, "signal": "bullish"},
            "ema": {"ema_12": 149.0, "ema_26": 147.0, "signal": "bullish"},
            "bollinger_bands": {"upper": 160, "middle": 150, "lower": 140, "bandwidth": 13.3, "signal": "neutral"},
            "overall_signal": "bullish",
            "signal_counts": {"bullish": 3, "bearish": 0, "neutral": 2},
        }
        alerts = score_asset("AAPL", quote, indicators)
        assert len(alerts) == 0

    def test_price_spike_alert(self):
        """Large positive move should trigger price alert."""
        quote = {"price": 150.0, "change_percent": 7.5, "volume": 100000000}
        alerts = score_asset("TSLA", quote, None)
        assert len(alerts) == 1
        assert alerts[0].type.value == "price"
        assert "surging" in alerts[0].title.lower()
        assert alerts[0].asset_symbol == "TSLA"

    def test_price_drop_alert(self):
        """Large negative move should trigger price alert."""
        quote = {"price": 100.0, "change_percent": -6.0, "volume": 80000000}
        alerts = score_asset("META", quote, None)
        assert len(alerts) == 1
        assert alerts[0].type.value == "price"
        assert "dropping" in alerts[0].title.lower()

    def test_rsi_oversold_alert(self):
        """RSI below 30 should trigger oversold alert."""
        indicators = {
            "rsi": {"value": 25.0, "signal": "bullish"},
            "macd": {"macd_line": -1, "signal_line": -0.5, "histogram": -0.5, "signal": "bearish"},
            "sma": {"signal": "bearish"},
            "ema": {"signal": "bearish"},
            "bollinger_bands": {"signal": "bullish"},
            "overall_signal": "bearish",
            "signal_counts": {"bullish": 2, "bearish": 3, "neutral": 0},
        }
        alerts = score_asset("GOOG", None, indicators)
        assert any("oversold" in a.title.lower() for a in alerts)

    def test_rsi_extreme_oversold_alert(self):
        """RSI below 20 should trigger high-severity alert."""
        indicators = {
            "rsi": {"value": 15.0, "signal": "bullish"},
            "macd": {"histogram": -1, "signal": "bearish"},
            "sma": {"signal": "bearish"},
            "ema": {"signal": "bearish"},
            "bollinger_bands": {"signal": "bullish"},
            "overall_signal": "bearish",
            "signal_counts": {"bullish": 2, "bearish": 3, "neutral": 0},
        }
        alerts = score_asset("XYZ", None, indicators)
        rsi_alerts = [a for a in alerts if "extremely oversold" in a.title.lower()]
        assert len(rsi_alerts) == 1
        assert rsi_alerts[0].severity.value == "high"
        assert rsi_alerts[0].suggested_action.value == "buy"

    def test_rsi_overbought_alert(self):
        """RSI above 70 should trigger overbought alert."""
        indicators = {
            "rsi": {"value": 75.0, "signal": "bearish"},
            "macd": {"histogram": 1, "signal": "bullish"},
            "sma": {"signal": "bullish"},
            "ema": {"signal": "bullish"},
            "bollinger_bands": {"signal": "bearish"},
            "overall_signal": "bullish",
            "signal_counts": {"bullish": 3, "bearish": 2, "neutral": 0},
        }
        alerts = score_asset("NVDA", None, indicators)
        assert any("overbought" in a.title.lower() for a in alerts)

    def test_multi_factor_bullish_convergence(self):
        """4+ bullish signals should trigger multi-factor alert."""
        indicators = {
            "rsi": {"value": 55.0, "signal": "neutral"},
            "macd": {"histogram": 1.5, "signal": "bullish"},
            "sma": {"signal": "bullish"},
            "ema": {"signal": "bullish"},
            "bollinger_bands": {"signal": "bullish"},
            "overall_signal": "bullish",
            "signal_counts": {"bullish": 4, "bearish": 0, "neutral": 1},
        }
        alerts = score_asset("AMZN", None, indicators)
        multi = [a for a in alerts if a.type.value == "multi_factor"]
        assert len(multi) == 1
        assert "bullish convergence" in multi[0].title.lower()

    def test_multi_factor_bearish_convergence(self):
        """4+ bearish signals should trigger multi-factor alert."""
        indicators = {
            "rsi": {"value": 45.0, "signal": "neutral"},
            "macd": {"histogram": -1.5, "signal": "bearish"},
            "sma": {"signal": "bearish"},
            "ema": {"signal": "bearish"},
            "bollinger_bands": {"signal": "bearish"},
            "overall_signal": "bearish",
            "signal_counts": {"bullish": 0, "bearish": 4, "neutral": 1},
        }
        alerts = score_asset("DIS", None, indicators)
        multi = [a for a in alerts if a.type.value == "multi_factor"]
        assert len(multi) == 1
        assert "bearish convergence" in multi[0].title.lower()

    def test_no_quote_no_indicators(self):
        """No data should produce no alerts."""
        alerts = score_asset("UNKNOWN", None, None)
        assert len(alerts) == 0


class TestAlertsRouter:
    """Integration tests for alerts API endpoints."""

    @pytest.mark.asyncio
    async def test_get_alerts_no_scan(self, client):
        """Default alerts endpoint returns empty without scan."""
        response = await client.get("/api/v1/alerts/")
        assert response.status_code == 200
        data = response.json()
        assert data["alerts"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_scan_single_asset(self, client):
        """Scan endpoint should return alerts for a symbol."""
        with patch("app.routers.alerts.scan_symbols", new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = []
            response = await client.get("/api/v1/alerts/scan/AAPL")

        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        mock_scan.assert_called_once()
        call_args = mock_scan.call_args[0][0]
        assert call_args[0]["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_scan_with_portfolio(self, client, mock_market_data):
        """Scan with portfolio holdings should scan those symbols."""
        # Add a holding first
        await client.post("/api/v1/portfolio/", json={
            "symbol": "MSFT", "name": "Microsoft", "type": "stock",
            "quantity": 10, "avg_buy_price": 400.0,
        })

        with patch("app.routers.alerts.scan_symbols", new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = []
            response = await client.get("/api/v1/alerts/?scan=true")

        assert response.status_code == 200
        call_args = mock_scan.call_args[0][0]
        symbols = [s["symbol"] for s in call_args]
        assert "MSFT" in symbols
