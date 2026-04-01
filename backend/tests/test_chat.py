"""Tests for chat/AI endpoints."""

from unittest.mock import AsyncMock, patch

import pytest


class _DummyDelta:
    def __init__(self, content: str):
        self.content = content


class _DummyChoice:
    def __init__(self, content: str):
        self.delta = _DummyDelta(content)


class _DummyChunk:
    def __init__(self, content: str):
        self.choices = [_DummyChoice(content)]


async def _fake_stream(tokens: list[str]):
    for token in tokens:
        yield _DummyChunk(token)


@pytest.mark.asyncio
async def test_ai_status_unconfigured(client):
    """AI status should report configured state based on API key."""
    with patch("app.services.groq_service.groq_service.is_available", return_value=False):
        response = await client.get("/api/v1/chat/status")

    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is False


@pytest.mark.asyncio
async def test_ai_status_configured(client):
    """AI status should report configured when key is set."""
    with patch("app.services.groq_service.groq_service.is_available", return_value=True):
        response = await client.get("/api/v1/chat/status")

    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is True


@pytest.mark.asyncio
async def test_chat_returns_503_when_unconfigured(client):
    """Chat should return 503 when AI is not configured."""
    with patch("app.services.groq_service.groq_service.is_available", return_value=False):
        response = await client.post("/api/v1/chat/", json={
            "messages": [{"role": "user", "content": "Hello"}],
        })

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_chat_success(client):
    """Chat should stream AI response when configured."""
    async def _stream_chat(**kwargs):
        return _fake_stream(["AAPL", " looks strong"])

    with patch("app.services.groq_service.groq_service.is_available", return_value=True), \
         patch("app.services.groq_service.groq_service.stream_chat", side_effect=_stream_chat):

        response = await client.post("/api/v1/chat/", json={
            "messages": [{"role": "user", "content": "What do you think about AAPL?"}],
        })

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "AAPL" in response.text
    assert "[DONE]" in response.text


@pytest.mark.asyncio
async def test_chat_multi_turn(client):
    """Chat should support multi-turn conversations."""
    async def _stream_chat(**kwargs):
        return _fake_stream(["More detail"])

    with patch("app.services.groq_service.groq_service.is_available", return_value=True), \
         patch("app.services.groq_service.groq_service.stream_chat", side_effect=_stream_chat) as mock_stream:

        response = await client.post("/api/v1/chat/", json={
            "messages": [
                {"role": "user", "content": "Analyze NVDA"},
                {"role": "assistant", "content": "NVDA is showing bullish signals."},
                {"role": "user", "content": "Tell me more"},
            ],
        })

    assert response.status_code == 200
    mock_stream.assert_called_once()
    call_args = mock_stream.call_args
    assert len(call_args.kwargs["messages"]) == 4


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
    """Asset analysis should fall back to structured explanation when no LLM is configured."""
    with patch("app.routers.chat.explain_asset_analysis", new_callable=AsyncMock) as mock_explain:
        mock_explain.return_value = {
            "symbol": "AAPL",
            "summary": "Fallback summary",
            "signal": "neutral",
            "confidence": 0.42,
            "confidence_label": "low",
            "warnings": ["Coverage is thin."],
            "contradictory_signals": [],
            "sources": ["technical_analysis"],
            "component_scores": {"total_score": 52.0},
            "generated_at": "2026-03-07T10:00:00+00:00",
            "decision_support_only": True,
        }
        response = await client.get("/api/v1/chat/analyze/AAPL")

    assert response.status_code == 200
    assert response.json()["summary"] == "Fallback summary"


@pytest.mark.asyncio
async def test_analyze_asset_success(client):
    """Asset analysis should return synthesized analysis."""
    with patch("app.routers.chat.explain_asset_analysis", new_callable=AsyncMock) as mock_explain:
        mock_explain.return_value = {
            "symbol": "AAPL",
            "summary": "AAPL shows bullish momentum across multiple indicators.",
            "signal": "bullish",
            "confidence": 0.78,
            "confidence_label": "high",
            "warnings": [],
            "contradictory_signals": ["Sentiment remains softer than technicals."],
            "sources": ["technical_analysis", "Yahoo Finance"],
            "component_scores": {"technical_score": 68.0, "total_score": 63.4},
            "generated_at": "2026-03-07T10:00:00+00:00",
            "decision_support_only": True,
        }

        response = await client.get("/api/v1/chat/analyze/AAPL")

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["signal"] == "bullish"
    assert 0 <= data["confidence"] <= 1
    assert len(data["summary"]) > 0
    assert "sources" in data
