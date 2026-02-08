"""Tests for WebSocket price streaming endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class TestWebSocket:
    @pytest.mark.asyncio
    async def test_websocket_connect_and_subscribe(self):
        """Client can connect and subscribe to price updates."""
        with patch("app.routers.ws.market_data_service") as mock_svc:
            mock_svc.get_quote = AsyncMock(return_value={
                "symbol": "AAPL",
                "price": 150.0,
                "change_percent": 1.2,
                "volume": 50000000,
            })

            from starlette.testclient import TestClient
            client = TestClient(app)

            with client.websocket_connect("/api/v1/ws/prices") as ws:
                ws.send_json({
                    "action": "subscribe",
                    "symbols": ["AAPL"],
                    "interval": 5,
                })

                # Should get subscribed confirmation
                resp = ws.receive_json()
                assert resp["type"] == "subscribed"
                assert resp["symbols"] == ["AAPL"]
                assert resp["interval"] == 5

                # Should get first price update
                resp = ws.receive_json()
                assert resp["type"] == "prices"
                assert len(resp["data"]) == 1
                assert resp["data"][0]["symbol"] == "AAPL"
                assert resp["data"][0]["price"] == 150.0

    @pytest.mark.asyncio
    async def test_websocket_invalid_json(self):
        """Server handles invalid JSON gracefully."""
        from starlette.testclient import TestClient
        client = TestClient(app)

        with client.websocket_connect("/api/v1/ws/prices") as ws:
            ws.send_text("not json")
            resp = ws.receive_json()
            assert resp["type"] == "error"
            assert "Invalid JSON" in resp["message"]

    @pytest.mark.asyncio
    async def test_websocket_empty_symbols(self):
        """Server rejects subscribe with empty symbols."""
        from starlette.testclient import TestClient
        client = TestClient(app)

        with client.websocket_connect("/api/v1/ws/prices") as ws:
            ws.send_json({"action": "subscribe", "symbols": []})
            resp = ws.receive_json()
            assert resp["type"] == "error"

    @pytest.mark.asyncio
    async def test_websocket_unknown_action(self):
        """Server responds with error for unknown action."""
        from starlette.testclient import TestClient
        client = TestClient(app)

        with client.websocket_connect("/api/v1/ws/prices") as ws:
            ws.send_json({"action": "foobar"})
            resp = ws.receive_json()
            assert resp["type"] == "error"
            assert "Unknown action" in resp["message"]

    @pytest.mark.asyncio
    async def test_websocket_unsubscribe(self):
        """Client can unsubscribe from price updates."""
        with patch("app.routers.ws.market_data_service") as mock_svc:
            mock_svc.get_quote = AsyncMock(return_value={
                "symbol": "MSFT",
                "price": 400.0,
                "change_percent": 0.5,
                "volume": 30000000,
            })

            from starlette.testclient import TestClient
            client = TestClient(app)

            with client.websocket_connect("/api/v1/ws/prices") as ws:
                ws.send_json({
                    "action": "subscribe",
                    "symbols": ["MSFT"],
                    "interval": 5,
                })
                # Consume subscribed + first price update
                ws.receive_json()  # subscribed
                ws.receive_json()  # prices

                ws.send_json({"action": "unsubscribe"})
                resp = ws.receive_json()
                assert resp["type"] == "unsubscribed"
