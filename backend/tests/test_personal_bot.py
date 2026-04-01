from unittest.mock import AsyncMock, PropertyMock, patch

import pytest

from app.schemas.asset import Alert, AlertSeverity, AlertType, SuggestedAction
from app.services.store import store
from app.services.telegram_service import TelegramService


def _bot_info():
    return {"first_name": "MyInvestIA Bot", "username": "myinvestia_test_bot"}


async def _connect_bot(client):
    response = await client.post("/api/v1/notifications/bot/connect")
    assert response.status_code == 200
    payload = response.json()
    code = payload["pending_code"]

    verify_response = await client.post("/api/v1/notifications/bot/verify")
    assert verify_response.status_code == 200
    return code, verify_response.json()


@pytest.mark.asyncio
async def test_personal_bot_connect_verify_and_test(client):
    with patch.object(TelegramService, "bot_available", new_callable=PropertyMock, return_value=True), \
         patch("app.services.personal_bot_service.telegram_service.get_bot_info", AsyncMock(return_value=_bot_info())), \
         patch("app.services.personal_bot_service.telegram_service.send_message_to_chat", AsyncMock(return_value={"ok": True})) as mock_send:
        connect_response = await client.post("/api/v1/notifications/bot/connect")
        assert connect_response.status_code == 200
        connect_payload = connect_response.json()
        code = connect_payload["pending_code"]
        assert code
        assert connect_payload["connect_url"].endswith(code)

        with patch(
            "app.services.personal_bot_service.telegram_service.get_updates",
            AsyncMock(
                return_value=[
                    {
                        "message": {
                            "text": f"/start {code}",
                            "chat": {"id": 123456, "title": "Darce"},
                            "from": {"id": 42, "username": "darce", "first_name": "Darce"},
                        }
                    }
                ]
            ),
        ):
            verify_response = await client.post("/api/v1/notifications/bot/verify")

        assert verify_response.status_code == 200
        verify_payload = verify_response.json()
        assert verify_payload["success"] is True
        assert verify_payload["status"]["connected"] is True
        assert verify_payload["status"]["chat_id"] == "123456"

        test_response = await client.post("/api/v1/notifications/bot/test")
        assert test_response.status_code == 200
        test_payload = test_response.json()
        assert test_payload["success"] is True
        assert mock_send.await_count >= 2


@pytest.mark.asyncio
async def test_personal_bot_run_and_provision_defaults(client):
    store.add_holding(
        "test-user",
        "AAPL",
        "Apple",
        "stock",
        3,
        180,
        tenant_id="default",
    )
    watchlist = store.create_watchlist("test-user", "Tech", tenant_id="default")
    store.add_asset_to_watchlist(
        "test-user",
        watchlist["id"],
        "NVDA",
        "NVIDIA",
        "stock",
        tenant_id="default",
    )

    with patch.object(TelegramService, "bot_available", new_callable=PropertyMock, return_value=True), \
         patch("app.services.personal_bot_service.telegram_service.get_bot_info", AsyncMock(return_value=_bot_info())), \
         patch("app.services.personal_bot_service.telegram_service.send_message_to_chat", AsyncMock(return_value={"ok": True})):
        connect_response = await client.post("/api/v1/notifications/bot/connect")
        code = connect_response.json()["pending_code"]

        with patch(
            "app.services.personal_bot_service.telegram_service.get_updates",
            AsyncMock(
                return_value=[
                    {
                        "message": {
                            "text": f"/start {code}",
                            "chat": {"id": 98765, "title": "Darce"},
                            "from": {"id": 7, "username": "darce", "first_name": "Darce"},
                        }
                    }
                ]
            ),
        ):
            verify_response = await client.post("/api/v1/notifications/bot/verify")
            assert verify_response.status_code == 200

        provision_response = await client.post("/api/v1/notifications/bot/provision-defaults")
        assert provision_response.status_code == 200
        provision_payload = provision_response.json()
        assert provision_payload["success"] is True
        assert provision_payload["created_rules"] == 3

        with patch(
            "app.services.personal_bot_service.build_briefing_from_inbox",
            AsyncMock(
                return_value={
                    "briefing": "Daily brief",
                    "suggestions": ["Open AAPL"],
                    "generated_at": "2026-03-06T00:00:00+00:00",
                    "preset": "premarket",
                    "top_inbox_items": [
                        {
                            "id": "inbox-1",
                            "scope": "portfolio",
                            "kind": "opportunity",
                            "title": "AAPL setup improving",
                            "summary": "Momentum and coverage improved",
                            "why_now": "Price/volume confirms upside",
                            "symbols": ["AAPL"],
                            "primary_symbol": "AAPL",
                        }
                    ],
                    "next_events": [
                        {
                            "id": "event-1",
                            "title": "AAPL earnings",
                            "symbol": "AAPL",
                        }
                    ],
                    "thesis_watch": [],
                }
            ),
        ), patch(
            "app.services.personal_bot_service.scan_symbols",
            AsyncMock(
                return_value=[
                    Alert(
                        id="alert-1",
                        type=AlertType.MULTI_FACTOR,
                        severity=AlertSeverity.HIGH,
                        title="AAPL breakout",
                        description="Momentum and trend align",
                        reasoning="Breakout with strong breadth",
                        confidence=0.82,
                        suggested_action=SuggestedAction.BUY,
                        created_at="2026-03-06T00:00:00+00:00",
                        asset_symbol="AAPL",
                    )
                ]
            ),
        ), patch(
            "app.services.personal_bot_service.list_theses",
            return_value=[
                {
                    "id": "thesis-1",
                    "symbol": "AAPL",
                    "review_state": "at_risk",
                    "invalidation": "Below 180",
                }
            ],
        ):
            run_response = await client.post("/api/v1/notifications/bot/run")

        assert run_response.status_code == 200
        run_payload = run_response.json()
        assert run_payload["success"] is True
        assert run_payload["sent_messages"] >= 2
        assert run_payload["sent_alerts"] == 1
        assert run_payload["status"]["last_alert_count"] == 1

        history_response = await client.get("/api/v1/notifications/bot/history")
        assert history_response.status_code == 200
        history_payload = history_response.json()
        assert len(history_payload) >= 1
