"""Tests for Telegram notification service and endpoints."""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest


class TestTelegramService:
    def test_not_configured_when_no_token(self):
        with patch("app.services.telegram_service.settings") as mock_settings:
            mock_settings.telegram_bot_token = ""
            mock_settings.telegram_chat_id = ""
            from app.services.telegram_service import TelegramService
            svc = TelegramService()
            assert not svc.configured

    def test_configured_when_token_and_chat_set(self):
        with patch("app.services.telegram_service.settings") as mock_settings:
            mock_settings.telegram_bot_token = "123:ABC"
            mock_settings.telegram_chat_id = "456"
            from app.services.telegram_service import TelegramService
            svc = TelegramService()
            assert svc.configured

    @pytest.mark.asyncio
    async def test_send_message_not_configured(self):
        with patch("app.services.telegram_service.settings") as mock_settings:
            mock_settings.telegram_bot_token = ""
            mock_settings.telegram_chat_id = ""
            from app.services.telegram_service import TelegramService
            svc = TelegramService()
            result = await svc.send_message("test")
            assert result is None

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        with patch("app.services.telegram_service.settings") as mock_settings:
            mock_settings.telegram_bot_token = "123:ABC"
            mock_settings.telegram_chat_id = "456"
            from app.services.telegram_service import TelegramService
            svc = TelegramService()

            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True, "result": {"message_id": 1}}
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.is_closed = False
            svc._http_client = mock_client

            result = await svc.send_message("Hello!")
            assert result is not None
            assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_send_message_api_error(self):
        with patch("app.services.telegram_service.settings") as mock_settings:
            mock_settings.telegram_bot_token = "123:ABC"
            mock_settings.telegram_chat_id = "456"
            from app.services.telegram_service import TelegramService
            svc = TelegramService()

            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": False, "description": "Bad Request"}
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.is_closed = False
            svc._http_client = mock_client

            result = await svc.send_message("Hello!")
            assert result is None

    @pytest.mark.asyncio
    async def test_send_alert_format(self):
        with patch("app.services.telegram_service.settings") as mock_settings:
            mock_settings.telegram_bot_token = "123:ABC"
            mock_settings.telegram_chat_id = "456"
            from app.services.telegram_service import TelegramService
            svc = TelegramService()

            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True, "result": {"message_id": 2}}
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.is_closed = False
            svc._http_client = mock_client

            result = await svc.send_alert({
                "title": "RSI Oversold",
                "description": "RSI dropped below 20",
                "severity": "high",
                "asset_symbol": "AAPL",
                "suggested_action": "buy",
                "confidence": 0.75,
            })
            assert result is not None
            # Verify the message content was formatted correctly
            call_args = mock_client.post.call_args
            sent_text = call_args.kwargs["json"]["text"]
            assert "RSI Oversold" in sent_text
            assert "AAPL" in sent_text
            assert "HIGH" in sent_text
            assert "BUY" in sent_text

    @pytest.mark.asyncio
    async def test_get_bot_info_not_configured(self):
        with patch("app.services.telegram_service.settings") as mock_settings:
            mock_settings.telegram_bot_token = ""
            mock_settings.telegram_chat_id = ""
            from app.services.telegram_service import TelegramService
            svc = TelegramService()
            result = await svc.get_bot_info()
            assert result is None


class TestNotificationsRouter:
    @pytest.mark.asyncio
    async def test_status_not_configured(self, client):
        with patch("app.routers.notifications.telegram_service") as mock_svc:
            mock_svc.configured = False
            response = await client.get("/api/v1/notifications/status")

        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is False

    @pytest.mark.asyncio
    async def test_status_configured(self, client):
        with patch("app.routers.notifications.telegram_service") as mock_svc:
            mock_svc.configured = True
            mock_svc.get_bot_info = AsyncMock(return_value={
                "first_name": "ORACLE Bot",
                "username": "oracle_bot",
            })
            response = await client.get("/api/v1/notifications/status")

        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is True
        assert data["bot_name"] == "ORACLE Bot"
        assert data["bot_username"] == "oracle_bot"

    @pytest.mark.asyncio
    async def test_send_not_configured(self, client):
        with patch("app.routers.notifications.telegram_service") as mock_svc:
            mock_svc.configured = False
            response = await client.post(
                "/api/v1/notifications/send",
                json={"message": "Hello"}
            )

        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_send_success(self, client):
        with patch("app.routers.notifications.telegram_service") as mock_svc:
            mock_svc.configured = True
            mock_svc.send_message = AsyncMock(return_value={"ok": True})
            response = await client.post(
                "/api/v1/notifications/send",
                json={"message": "Hello from ORACLE"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_send_failure(self, client):
        with patch("app.routers.notifications.telegram_service") as mock_svc:
            mock_svc.configured = True
            mock_svc.send_message = AsyncMock(return_value=None)
            response = await client.post(
                "/api/v1/notifications/send",
                json={"message": "Hello"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_send_alert_success(self, client):
        with patch("app.routers.notifications.telegram_service") as mock_svc:
            mock_svc.configured = True
            mock_svc.send_alert = AsyncMock(return_value={"ok": True})
            response = await client.post(
                "/api/v1/notifications/send-alert",
                json={
                    "title": "Price Spike",
                    "description": "AAPL up 8%",
                    "severity": "high",
                    "asset_symbol": "AAPL",
                    "suggested_action": "monitor",
                    "confidence": 0.8,
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_send_alert_not_configured(self, client):
        with patch("app.routers.notifications.telegram_service") as mock_svc:
            mock_svc.configured = False
            response = await client.post(
                "/api/v1/notifications/send-alert",
                json={"title": "Test Alert"}
            )

        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_test_notification_success(self, client):
        with patch("app.routers.notifications.telegram_service") as mock_svc:
            mock_svc.configured = True
            mock_svc.send_test_message = AsyncMock(return_value={"ok": True})
            response = await client.post("/api/v1/notifications/test", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_test_notification_not_configured(self, client):
        with patch("app.routers.notifications.telegram_service") as mock_svc:
            mock_svc.configured = False
            response = await client.post("/api/v1/notifications/test", json={})

        assert response.status_code == 503
