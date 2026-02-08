"""Tests for sentiment analysis service and endpoint."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.sentiment_service import (
    analyze_sentiment,
    _parse_sentiment_response,
    _default_sentiment,
)


class TestDefaultSentiment:
    def test_returns_neutral(self):
        result = _default_sentiment("AAPL")
        assert result["symbol"] == "AAPL"
        assert result["score"] == 0.0
        assert result["label"] == "neutral"
        assert result["sources_count"] == 0
        assert "unavailable" in result["narrative"].lower() or "configure" in result["narrative"].lower()


class TestParseSentimentResponse:
    def test_valid_json(self):
        response = json.dumps({
            "score": 0.65,
            "label": "bullish",
            "sources_count": 5,
            "narrative": "Strong momentum with positive earnings outlook.",
            "key_factors": ["Earnings beat", "Strong guidance"],
        })
        result = _parse_sentiment_response(response, "AAPL")
        assert result["symbol"] == "AAPL"
        assert result["score"] == 0.65
        assert result["label"] == "bullish"
        assert result["sources_count"] == 5
        assert "momentum" in result["narrative"]
        assert len(result["key_factors"]) == 2

    def test_json_in_code_block(self):
        response = '```json\n{"score": -0.4, "label": "bearish", "sources_count": 3, "narrative": "Declining.", "key_factors": []}\n```'
        result = _parse_sentiment_response(response, "TSLA")
        assert result["score"] == -0.4
        assert result["label"] == "bearish"

    def test_score_clamped(self):
        response = json.dumps({"score": 2.5, "label": "bullish", "sources_count": 1, "narrative": "Test", "key_factors": []})
        result = _parse_sentiment_response(response, "TEST")
        assert result["score"] == 1.0

    def test_score_clamped_negative(self):
        response = json.dumps({"score": -3.0, "label": "bearish", "sources_count": 1, "narrative": "Test", "key_factors": []})
        result = _parse_sentiment_response(response, "TEST")
        assert result["score"] == -1.0

    def test_invalid_label_derived_from_score(self):
        response = json.dumps({"score": 0.8, "label": "invalid_label", "sources_count": 1, "narrative": "Test", "key_factors": []})
        result = _parse_sentiment_response(response, "TEST")
        assert result["label"] == "bullish"

    def test_invalid_json_returns_default(self):
        result = _parse_sentiment_response("not json at all", "AAPL")
        assert result["score"] == 0.0
        assert result["label"] == "neutral"

    def test_neutral_label_from_low_score(self):
        response = json.dumps({"score": 0.1, "label": "wrong", "sources_count": 1, "narrative": "Test", "key_factors": []})
        result = _parse_sentiment_response(response, "TEST")
        assert result["label"] == "neutral"


class TestAnalyzeSentiment:
    @pytest.mark.asyncio
    async def test_not_configured_returns_default(self):
        with patch("app.services.sentiment_service.ai_service") as mock_ai:
            mock_ai.is_configured = False
            result = await analyze_sentiment("AAPL")
            assert result["label"] == "neutral"
            assert result["sources_count"] == 0

    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        mock_response = json.dumps({
            "score": 0.5,
            "label": "bullish",
            "sources_count": 4,
            "narrative": "Positive outlook.",
            "key_factors": ["Strong earnings"],
        })
        with patch("app.services.sentiment_service.ai_service") as mock_ai:
            mock_ai.is_configured = True
            mock_ai.chat = AsyncMock(return_value=mock_response)
            result = await analyze_sentiment(
                "AAPL",
                quote_data={"price": 195.0, "change_percent": 1.2, "volume": 55000000},
            )
            assert result["score"] == 0.5
            assert result["label"] == "bullish"

    @pytest.mark.asyncio
    async def test_exception_returns_default(self):
        with patch("app.services.sentiment_service.ai_service") as mock_ai:
            mock_ai.is_configured = True
            mock_ai.chat = AsyncMock(side_effect=Exception("API error"))
            result = await analyze_sentiment("AAPL")
            assert result["label"] == "neutral"
            assert result["score"] == 0.0


class TestSentimentRouter:
    @pytest.mark.asyncio
    async def test_sentiment_endpoint(self, client):
        mock_result = {
            "symbol": "AAPL",
            "score": 0.6,
            "label": "bullish",
            "sources_count": 3,
            "narrative": "Strong bullish momentum.",
            "key_factors": ["Positive earnings"],
        }
        with patch("app.routers.market.market_data_service") as mock_mkt, \
             patch("app.routers.market.analyze_sentiment", new_callable=AsyncMock) as mock_sent:
            mock_mkt.get_quote = AsyncMock(return_value={"price": 195.0, "change_percent": 1.0, "volume": 50000000})
            mock_mkt.get_history = MagicMock(return_value=[])
            mock_sent.return_value = mock_result

            response = await client.get("/api/v1/market/sentiment/AAPL")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["score"] == 0.6
        assert data["label"] == "bullish"
        assert data["narrative"] == "Strong bullish momentum."

    @pytest.mark.asyncio
    async def test_sentiment_with_technical_data(self, client):
        mock_history = [
            {"date": f"2025-01-{i+1:02d}", "open": 100 + i, "high": 102 + i,
             "low": 99 + i, "close": 101.0 + i * 0.5, "volume": 1000000}
            for i in range(60)
        ]
        mock_result = {
            "symbol": "MSFT",
            "score": -0.3,
            "label": "bearish",
            "sources_count": 5,
            "narrative": "Weakness in tech sector.",
            "key_factors": ["Revenue miss"],
        }
        with patch("app.routers.market.market_data_service") as mock_mkt, \
             patch("app.routers.market.analyze_sentiment", new_callable=AsyncMock) as mock_sent:
            mock_mkt.get_quote = AsyncMock(return_value=None)
            mock_mkt.get_history = MagicMock(return_value=mock_history)
            mock_sent.return_value = mock_result

            response = await client.get("/api/v1/market/sentiment/MSFT")

        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "bearish"
