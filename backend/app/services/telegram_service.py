"""Telegram Bot API integration for sending notifications and alerts.

Supports the legacy global chat flow and per-user personal bot delivery.
"""

import html
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramService:
    """Sends messages via Telegram Bot API."""

    def __init__(self):
        self._http_client: httpx.AsyncClient | None = None

    @property
    def configured(self) -> bool:
        return bool(settings.telegram_bot_token and settings.telegram_chat_id)

    @property
    def bot_available(self) -> bool:
        return bool(settings.telegram_bot_token)

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=15.0)
        return self._http_client

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def send_message_to_chat(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "HTML",
    ) -> dict | None:
        """Send a text message to a specific Telegram chat.

        Args:
            chat_id: Telegram chat identifier
            text: Message content (supports HTML formatting)
            parse_mode: Telegram parse mode (HTML or MarkdownV2)

        Returns:
            Telegram API response dict, or None on failure
        """
        if not self.bot_available:
            logger.warning("Telegram bot token not configured — skipping message")
            return None

        try:
            client = await self._get_http_client()
            url = f"{TELEGRAM_API_BASE}/bot{settings.telegram_bot_token}/sendMessage"
            resp = await client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                logger.warning("Telegram API error: %s", data.get("description"))
                return None
            return data
        except Exception as e:
            logger.warning("Telegram send failed: %s", e)
            return None

    async def send_message(self, text: str, parse_mode: str = "HTML") -> dict | None:
        """Send a text message to the configured global Telegram chat."""
        if not self.configured:
            logger.warning("Telegram not configured — skipping message")
            return None
        return await self.send_message_to_chat(
            settings.telegram_chat_id,
            text,
            parse_mode=parse_mode,
        )

    async def send_alert_to_chat(self, chat_id: str, alert: dict) -> dict | None:
        """Format and send an alert notification via Telegram.

        Args:
            alert: Alert dict with keys: title, description, severity, asset_symbol, etc.

        Returns:
            Telegram API response dict, or None on failure
        """
        severity = alert.get("severity", "low").upper()
        severity_emoji = {
            "LOW": "\u2139\ufe0f",
            "MEDIUM": "\u26a0\ufe0f",
            "HIGH": "\u2757",
            "CRITICAL": "\ud83d\udea8",
        }.get(severity, "\u2139\ufe0f")

        symbol = alert.get("asset_symbol", "N/A")
        title = alert.get("title", "Alert")
        description = alert.get("description", "")
        reason = alert.get("reason", "") or alert.get("reasoning", "")
        action = alert.get("suggested_action", "monitor").upper()
        confidence = alert.get("confidence", 0.0)
        sources = ", ".join(alert.get("sources", [])[:3])

        text = (
            f"{severity_emoji} <b>InvestIA Alert — {severity}</b>\n\n"
            f"<b>{html.escape(str(title))}</b>\n"
            f"Symbol: <code>{html.escape(str(symbol))}</code>\n"
            f"{html.escape(str(description))}\n"
            f"{html.escape(str(reason))}\n\n"
            f"Action: <b>{action}</b> (confidence: {confidence:.0%})"
        )
        if sources:
            text += f"\nSources: <i>{html.escape(sources)}</i>"

        return await self.send_message_to_chat(chat_id, text)

    async def send_alert(self, alert: dict) -> dict | None:
        """Send an alert via the configured global Telegram chat."""
        if not self.configured:
            logger.warning("Telegram not configured — skipping alert")
            return None
        return await self.send_alert_to_chat(settings.telegram_chat_id, alert)

    async def send_test_message(self) -> dict | None:
        """Send a test message to verify Telegram configuration."""
        return await self.send_message(
            "\u2705 <b>InvestIA Connected</b>\n\n"
            "Telegram notifications are working correctly."
        )

    async def get_bot_info(self) -> dict | None:
        """Get info about the configured shared bot (for status check)."""
        if not self.bot_available:
            return None

        try:
            client = await self._get_http_client()
            url = f"{TELEGRAM_API_BASE}/bot{settings.telegram_bot_token}/getMe"
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if data.get("ok"):
                return data.get("result")
            return None
        except Exception as e:
            logger.warning("Telegram getMe failed: %s", e)
            return None

    async def get_updates(self, *, limit: int = 100) -> list[dict]:
        """Get recent bot updates for connect/verify flows."""
        if not self.bot_available:
            return []

        try:
            client = await self._get_http_client()
            url = f"{TELEGRAM_API_BASE}/bot{settings.telegram_bot_token}/getUpdates"
            resp = await client.get(url, params={"limit": limit, "timeout": 0})
            resp.raise_for_status()
            data = resp.json()
            if data.get("ok"):
                return data.get("result", [])
            return []
        except Exception as e:
            logger.warning("Telegram getUpdates failed: %s", e)
            return []


# Singleton
telegram_service = TelegramService()
