"""Tests for chat/AI endpoints.

Mocks the Anthropic API to avoid real API calls and key requirements.
"""

from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest


@pytest.mark.asyncio
async def test_ai_status_unconfigured(client):
    """AI status should report configured state based on API key."""
    with patch("app.routers.chat.ai_service") as mock_svc:
        type(mock_svc).is_configured = PropertyMock(return_value=False)
        response = await client.get("/api/v1/chat/status")

    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is False


@pytest.mark.asyncio
async def test_ai_status_configured(client):
    """AI status should report configured when key is set."""
    with patch("app.routers.chat.ai_service") as mock_svc:
        type(mock_svc).is_configured = PropertyMock(return_value=True)
        response = await client.get("/api/v1/chat/status")

    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is True


@pytest.mark.asyncio
async def test_chat_returns_503_when_unconfigured(client):
    """Chat should return 503 when AI is not configured."""
    with patch("app.routers.chat.ai_service") as mock_svc:
        type(mock_svc).is_configured = PropertyMock(return_value=False)
        response = await client.post("/api/v1/chat/", json={
            "messages": [{"role": "user", "content": "Hello"}],
        })

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_chat_success(client):
    """Chat should return AI response when configured."""
    with patch("app.routers.chat.ai_service") as mock_svc:
        type(mock_svc).is_configured = PropertyMock(return_value=True)
        mock_svc.chat = AsyncMock(return_value="AAPL looks strong based on technical indicators.")

        response = await client.post("/api/v1/chat/", json={
            "messages": [{"role": "user", "content": "What do you think about AAPL?"}],
        })

    assert response.status_code == 200
    data = response.json()
    assert "AAPL" in data["response"]
    assert data["model"] == "claude-sonnet-4-5-20250929"


@pytest.mark.asyncio
async def test_chat_multi_turn(client):
    """Chat should support multi-turn conversations."""
    with patch("app.routers.chat.ai_service") as mock_svc:
        type(mock_svc).is_configured = PropertyMock(return_value=True)
        mock_svc.chat = AsyncMock(return_value="Here's more detail on that analysis.")

        response = await client.post("/api/v1/chat/", json={
            "messages": [
                {"role": "user", "content": "Analyze NVDA"},
                {"role": "assistant", "content": "NVDA is showing bullish signals."},
                {"role": "user", "content": "Tell me more"},
            ],
        })

    assert response.status_code == 200
    mock_svc.chat.assert_called_once()
    call_args = mock_svc.chat.call_args
    assert len(call_args.kwargs["messages"]) == 3


@pytest.mark.asyncio
async def test_chat_validation_empty_messages(client):
    """Chat should reject empty messages list."""
    response = await client.post("/api/v1/chat/", json={
        "messages": [],
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_validation_invalid_role(client):
    """Chat should reject invalid message roles."""
    response = await client.post("/api/v1/chat/", json={
        "messages": [{"role": "system", "content": "Hello"}],
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analyze_asset_returns_503_when_unconfigured(client):
    """Asset analysis should return 503 when AI is not configured."""
    with patch("app.routers.chat.ai_service") as mock_svc:
        type(mock_svc).is_configured = PropertyMock(return_value=False)
        response = await client.get("/api/v1/chat/analyze/AAPL")

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_analyze_asset_success(client):
    """Asset analysis should return synthesized analysis."""
    with patch("app.routers.chat.ai_service") as mock_svc, \
         patch("app.routers.chat.market_data_service") as mock_market, \
         patch("app.routers.chat.compute_all_indicators") as mock_ta:

        type(mock_svc).is_configured = PropertyMock(return_value=True)
        mock_market.get_quote = AsyncMock(return_value={
            "symbol": "AAPL", "name": "Apple", "price": 195.0,
            "change_percent": 1.2, "volume": 55000000,
        })
        mock_market.get_history = MagicMock(return_value=[
            {"close": 190 + i * 0.1} for i in range(60)
        ])
        mock_ta.return_value = {
            "rsi": {"value": 55.0, "signal": "neutral"},
            "macd": {"macd_line": 0.5, "signal_line": 0.3, "histogram": 0.2, "signal": "bullish"},
            "sma": {"sma_20": 192.0, "sma_50": 188.0, "signal": "bullish"},
            "ema": {"ema_12": 193.0, "ema_26": 190.0, "signal": "bullish"},
            "bollinger_bands": {"upper": 200, "middle": 192, "lower": 184, "bandwidth": 8.3, "signal": "neutral"},
            "overall_signal": "bullish",
            "signal_counts": {"bullish": 3, "bearish": 0, "neutral": 2},
        }
        mock_svc.analyze_asset = AsyncMock(return_value={
            "symbol": "AAPL",
            "summary": "AAPL shows bullish momentum across multiple indicators.",
            "signal": "bullish",
            "confidence": 0.6,
        })

        response = await client.get("/api/v1/chat/analyze/AAPL")

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["signal"] == "bullish"
    assert 0 <= data["confidence"] <= 1
    assert len(data["summary"]) > 0
