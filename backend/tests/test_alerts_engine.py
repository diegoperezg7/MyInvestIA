"""Tests for the alerts engine (scan + Telegram delivery)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.asset import Alert, AlertSeverity, AlertType, SuggestedAction
from app.services.alerts_engine import scan_and_notify, _meets_threshold


def _make_test_alert(severity: AlertSeverity, symbol: str = "AAPL") -> Alert:
    return Alert(
        id="test-id",
        type=AlertType.PRICE,
        severity=severity,
        title=f"{symbol} alert",
        description="Test alert",
        reasoning="Test reasoning",
        confidence=0.7,
        suggested_action=SuggestedAction.MONITOR,
        created_at="2025-01-01T00:00:00Z",
        asset_symbol=symbol,
    )


class TestMeetsThreshold:
    def test_high_meets_high(self):
        alert = _make_test_alert(AlertSeverity.HIGH)
        assert _meets_threshold(alert, AlertSeverity.HIGH) is True

    def test_medium_fails_high(self):
        alert = _make_test_alert(AlertSeverity.MEDIUM)
        assert _meets_threshold(alert, AlertSeverity.HIGH) is False

    def test_critical_meets_high(self):
        alert = _make_test_alert(AlertSeverity.CRITICAL)
        assert _meets_threshold(alert, AlertSeverity.HIGH) is True

    def test_low_meets_all(self):
        alert = _make_test_alert(AlertSeverity.LOW)
        assert _meets_threshold(alert, AlertSeverity.LOW) is True

    def test_medium_meets_medium(self):
        alert = _make_test_alert(AlertSeverity.MEDIUM)
        assert _meets_threshold(alert, AlertSeverity.MEDIUM) is True


class TestScanAndNotify:
    @pytest.mark.asyncio
    async def test_no_alerts_no_notifications(self):
        with patch("app.services.alerts_engine.scan_symbols", new_callable=AsyncMock) as mock_scan, \
             patch("app.services.alerts_engine.telegram_service") as mock_tg:
            mock_scan.return_value = []
            mock_tg.configured = True

            result = await scan_and_notify([{"symbol": "AAPL", "type": "stock"}])

            assert result["total_alerts"] == 0
            assert result["total_notified"] == 0
            assert result["telegram_configured"] is True

    @pytest.mark.asyncio
    async def test_high_alert_sends_notification(self):
        alert = _make_test_alert(AlertSeverity.HIGH)
        with patch("app.services.alerts_engine.scan_symbols", new_callable=AsyncMock) as mock_scan, \
             patch("app.services.alerts_engine.telegram_service") as mock_tg:
            mock_scan.return_value = [alert]
            mock_tg.configured = True
            mock_tg.send_alert = AsyncMock(return_value={"ok": True})

            result = await scan_and_notify(
                [{"symbol": "AAPL", "type": "stock"}],
                min_severity="high",
            )

            assert result["total_alerts"] == 1
            assert result["total_notified"] == 1
            assert len(result["notified"]) == 1
            assert result["notified"][0]["delivered"] is True
            mock_tg.send_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_high_alert_uses_personal_chat_when_available(self):
        alert = _make_test_alert(AlertSeverity.HIGH)
        with patch("app.services.alerts_engine.scan_symbols", new_callable=AsyncMock) as mock_scan, \
             patch("app.services.alerts_engine.telegram_service") as mock_tg:
            mock_scan.return_value = [alert]
            mock_tg.configured = False
            mock_tg.send_alert_to_chat = AsyncMock(return_value={"ok": True})

            result = await scan_and_notify(
                [{"symbol": "AAPL", "type": "stock"}],
                min_severity="high",
                chat_id="123456",
            )

            assert result["total_alerts"] == 1
            assert result["total_notified"] == 1
            assert result["telegram_configured"] is True
            mock_tg.send_alert_to_chat.assert_called_once()
            mock_tg.send_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_medium_alert_skipped_with_high_threshold(self):
        alert = _make_test_alert(AlertSeverity.MEDIUM)
        with patch("app.services.alerts_engine.scan_symbols", new_callable=AsyncMock) as mock_scan, \
             patch("app.services.alerts_engine.telegram_service") as mock_tg:
            mock_scan.return_value = [alert]
            mock_tg.configured = True

            result = await scan_and_notify(
                [{"symbol": "AAPL", "type": "stock"}],
                min_severity="high",
            )

            assert result["total_alerts"] == 1
            assert result["total_notified"] == 0
            assert len(result["notified"]) == 0

    @pytest.mark.asyncio
    async def test_telegram_not_configured(self):
        alert = _make_test_alert(AlertSeverity.HIGH)
        with patch("app.services.alerts_engine.scan_symbols", new_callable=AsyncMock) as mock_scan, \
             patch("app.services.alerts_engine.telegram_service") as mock_tg:
            mock_scan.return_value = [alert]
            mock_tg.configured = False

            result = await scan_and_notify(
                [{"symbol": "AAPL", "type": "stock"}],
                min_severity="high",
            )

            assert result["total_alerts"] == 1
            assert result["total_notified"] == 0
            assert result["telegram_configured"] is False

    @pytest.mark.asyncio
    async def test_telegram_send_failure(self):
        alert = _make_test_alert(AlertSeverity.HIGH)
        with patch("app.services.alerts_engine.scan_symbols", new_callable=AsyncMock) as mock_scan, \
             patch("app.services.alerts_engine.telegram_service") as mock_tg:
            mock_scan.return_value = [alert]
            mock_tg.configured = True
            mock_tg.send_alert = AsyncMock(return_value=None)

            result = await scan_and_notify(
                [{"symbol": "AAPL", "type": "stock"}],
                min_severity="high",
            )

            assert result["total_alerts"] == 1
            assert result["total_notified"] == 0
            assert result["notified"][0]["delivered"] is False

    @pytest.mark.asyncio
    async def test_all_severity_sends_everything(self):
        alerts = [
            _make_test_alert(AlertSeverity.LOW, "SPY"),
            _make_test_alert(AlertSeverity.MEDIUM, "QQQ"),
            _make_test_alert(AlertSeverity.HIGH, "AAPL"),
        ]
        with patch("app.services.alerts_engine.scan_symbols", new_callable=AsyncMock) as mock_scan, \
             patch("app.services.alerts_engine.telegram_service") as mock_tg:
            mock_scan.return_value = alerts
            mock_tg.configured = True
            mock_tg.send_alert = AsyncMock(return_value={"ok": True})

            result = await scan_and_notify(
                [{"symbol": "AAPL", "type": "stock"}],
                min_severity="all",
            )

            assert result["total_alerts"] == 3
            assert result["total_notified"] == 3

    @pytest.mark.asyncio
    async def test_portfolio_alerts_are_included(self):
        with patch("app.services.alerts_engine.scan_symbols", new_callable=AsyncMock) as mock_scan, \
             patch("app.services.alerts_engine.build_portfolio_alerts", new_callable=AsyncMock) as mock_portfolio, \
             patch("app.services.alerts_engine.telegram_service") as mock_tg:
            mock_scan.return_value = []
            mock_portfolio.return_value = [_make_test_alert(AlertSeverity.HIGH, "AAPL")]
            mock_tg.configured = False

            result = await scan_and_notify(
                [{"symbol": "AAPL", "type": "stock"}],
                portfolio_holdings=[{"symbol": "AAPL"}],
            )

            assert result["total_alerts"] == 1
            assert result["total_notified"] == 0


class TestScanAndNotifyRouter:
    @pytest.mark.asyncio
    async def test_scan_and_notify_endpoint(self, client):
        alert = _make_test_alert(AlertSeverity.HIGH)
        with patch("app.routers.alerts.scan_and_notify", new_callable=AsyncMock) as mock_engine:
            mock_engine.return_value = {
                "alerts": [alert],
                "notified": [
                    {"alert_id": "test-id", "symbol": "AAPL",
                     "title": "AAPL alert", "severity": "high", "delivered": True}
                ],
                "total_alerts": 1,
                "total_notified": 1,
                "telegram_configured": True,
            }
            response = await client.post("/api/v1/alerts/scan-and-notify?min_severity=high")

        assert response.status_code == 200
        data = response.json()
        assert data["total_alerts"] == 1
        assert data["total_notified"] == 1
        assert len(data["notified"]) == 1
        assert data["notified"][0]["delivered"] is True
        assert data["telegram_configured"] is True

    @pytest.mark.asyncio
    async def test_scan_and_notify_no_alerts(self, client):
        with patch("app.routers.alerts.scan_and_notify", new_callable=AsyncMock) as mock_engine:
            mock_engine.return_value = {
                "alerts": [],
                "notified": [],
                "total_alerts": 0,
                "total_notified": 0,
                "telegram_configured": False,
            }
            response = await client.post("/api/v1/alerts/scan-and-notify")

        assert response.status_code == 200
        data = response.json()
        assert data["total_alerts"] == 0
        assert data["telegram_configured"] is False
