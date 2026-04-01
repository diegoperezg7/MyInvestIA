"""Tests for macro intelligence service and market macro endpoint."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.macro_intelligence import (
    get_macro_indicator,
    get_all_macro_indicators,
    get_macro_summary,
    _get_trend,
    _vix_impact,
    _dxy_impact,
    _yield_impact,
    _commodity_impact,
)


class TestTrend:
    def test_up_trend(self):
        assert _get_trend(1.5) == "up"

    def test_down_trend(self):
        assert _get_trend(-0.8) == "down"

    def test_stable_trend(self):
        assert _get_trend(0.1) == "stable"

    def test_boundary_stable(self):
        assert _get_trend(0.3) == "stable"
        assert _get_trend(-0.3) == "stable"


class TestVIXImpact:
    def test_extreme_fear(self):
        result = _vix_impact(35.0)
        assert "extreme" in result.lower() or "Extreme" in result

    def test_elevated(self):
        result = _vix_impact(22.0)
        assert "elevated" in result.lower() or "uncertainty" in result.lower()

    def test_normal(self):
        result = _vix_impact(17.0)
        assert "normal" in result.lower() or "balanced" in result.lower()

    def test_low(self):
        result = _vix_impact(12.0)
        assert "low" in result.lower() or "calm" in result.lower()


class TestDXYImpact:
    def test_strengthening(self):
        result = _dxy_impact(1.0)
        assert "strengthening" in result.lower()

    def test_weakening(self):
        result = _dxy_impact(-0.8)
        assert "weakening" in result.lower()

    def test_stable(self):
        result = _dxy_impact(0.2)
        assert "stable" in result.lower()


class TestYieldImpact:
    def test_elevated_rising(self):
        result = _yield_impact(5.2, 0.8)
        assert "elevated" in result.lower()
        assert "rising" in result.lower()

    def test_moderate_falling(self):
        result = _yield_impact(4.3, -0.7)
        assert "moderately" in result.lower()
        assert "falling" in result.lower()

    def test_low_stable(self):
        result = _yield_impact(3.5, 0.1)
        assert "stable" in result.lower()


class TestCommodityImpact:
    def test_gold_rally(self):
        result = _commodity_impact("Gold Futures", 1.5)
        assert "gold" in result.lower()
        assert "safe-haven" in result.lower() or "rallying" in result.lower()

    def test_gold_decline(self):
        result = _commodity_impact("Gold Futures", -1.5)
        assert "declining" in result.lower() or "risk-on" in result.lower()

    def test_oil_surge(self):
        result = _commodity_impact("Crude Oil WTI", 3.0)
        assert "oil" in result.lower()
        assert "surging" in result.lower()

    def test_oil_drop(self):
        result = _commodity_impact("Crude Oil WTI", -3.0)
        assert "dropping" in result.lower()


class TestGetMacroIndicator:
    @pytest.mark.asyncio
    async def test_unknown_ticker(self):
        with patch("app.services.macro_intelligence.get_all_macro_indicators", new_callable=AsyncMock, return_value=[]):
            assert await get_macro_indicator("UNKNOWN") is None

    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        with patch(
            "app.services.macro_intelligence.get_all_macro_indicators",
            new_callable=AsyncMock,
            return_value=[
                {
                    "name": "VIX (Volatility Index)",
                    "ticker": "^VIX",
                    "value": 18.5,
                    "category": "volatility",
                    "trend": "stable",
                    "impact_description": "Normal volatility",
                }
            ],
        ):
            result = await get_macro_indicator("^VIX")
        assert result is not None
        assert result["name"] == "VIX (Volatility Index)"
        assert result["value"] == 18.5
        assert result["category"] == "volatility"
        assert "trend" in result
        assert "impact_description" in result

    @pytest.mark.asyncio
    async def test_no_match_returns_none(self):
        with patch(
            "app.services.macro_intelligence.get_all_macro_indicators",
            new_callable=AsyncMock,
            return_value=[
                {"name": "US Dollar Index (DXY)", "ticker": "DX-Y.NYB", "value": 104.2, "trend": "up"}
            ],
        ):
            result = await get_macro_indicator("^VIX")
        assert result is None


class TestGetAllMacroIndicators:
    @pytest.mark.asyncio
    async def test_returns_only_successful(self):
        with patch(
            "app.services.macro_intelligence.macro_provider_chain.get_indicators",
            new_callable=AsyncMock,
            return_value=[
                {"name": "VIX (Volatility Index)", "ticker": "^VIX", "value": 18.5},
                {"name": "US Dollar Index (DXY)", "ticker": "DX-Y.NYB", "value": 104.2},
            ],
        ):
            results = await get_all_macro_indicators()
        assert len(results) == 2
        assert results[0]["name"] == "VIX (Volatility Index)"
        assert results[1]["name"] == "US Dollar Index (DXY)"


class TestGetMacroSummary:
    def test_empty_indicators(self):
        summary = get_macro_summary([])
        assert summary["environment"] == "unknown"
        assert summary["risk_level"] == "unknown"

    def test_high_vix_risk_off(self):
        indicators = [
            {"name": "VIX (Volatility Index)", "value": 32.0, "change_percent": 5.0, "trend": "up"},
            {"name": "US Dollar Index (DXY)", "value": 105.0, "change_percent": 0.6, "trend": "up"},
        ]
        summary = get_macro_summary(indicators)
        assert summary["risk_level"] == "high"
        assert summary["environment"] == "risk-off"
        assert len(summary["key_signals"]) > 0

    def test_low_vix_risk_on(self):
        indicators = [
            {"name": "VIX (Volatility Index)", "value": 12.0, "change_percent": -1.0, "trend": "down"},
        ]
        summary = get_macro_summary(indicators)
        assert summary["risk_level"] == "low"
        assert summary["environment"] == "risk-on"

    def test_rising_yields_signal(self):
        indicators = [
            {"name": "VIX (Volatility Index)", "value": 18.0, "change_percent": 0.2, "trend": "stable"},
            {"name": "10-Year Treasury Yield", "value": 4.5, "change_percent": 0.8, "trend": "up"},
        ]
        summary = get_macro_summary(indicators)
        signals = summary["key_signals"]
        assert any("rising" in s.lower() or "yield" in s.lower() for s in signals)

    def test_gold_rising_signal(self):
        indicators = [
            {"name": "VIX (Volatility Index)", "value": 20.0, "change_percent": 0.5, "trend": "up"},
            {"name": "Gold Futures", "value": 2100.0, "change_percent": 1.2, "trend": "up"},
        ]
        summary = get_macro_summary(indicators)
        signals = summary["key_signals"]
        assert any("gold" in s.lower() for s in signals)

    def test_oil_surge_signal(self):
        indicators = [
            {"name": "VIX (Volatility Index)", "value": 18.0, "change_percent": 0.1, "trend": "stable"},
            {"name": "Crude Oil WTI", "value": 85.0, "change_percent": 3.5, "trend": "up"},
        ]
        summary = get_macro_summary(indicators)
        signals = summary["key_signals"]
        assert any("oil" in s.lower() for s in signals)


class TestMacroRouter:
    @pytest.mark.asyncio
    async def test_get_macro_endpoint(self, client):
        with patch("app.routers.market.get_all_macro_indicators") as mock_all, \
             patch("app.routers.market.get_macro_summary") as mock_summary, \
             patch("app.routers.market.get_macro_context", new_callable=AsyncMock) as mock_context:
            mock_all.return_value = [
                {
                    "name": "VIX (Volatility Index)",
                    "value": 18.5,
                    "change_percent": 1.2,
                    "previous_close": 18.28,
                    "trend": "up",
                    "impact_description": "Normal volatility",
                    "category": "volatility",
                },
            ]
            mock_summary.return_value = {
                "environment": "neutral",
                "risk_level": "moderate",
                "key_signals": [],
            }
            mock_context.return_value = {"sources": [], "official_series": [], "fear_greed": None}
            response = await client.get("/api/v1/market/macro")

        assert response.status_code == 200
        data = response.json()
        assert "indicators" in data
        assert "summary" in data
        assert len(data["indicators"]) == 1
        assert data["indicators"][0]["name"] == "VIX (Volatility Index)"
        assert data["summary"]["environment"] == "neutral"
