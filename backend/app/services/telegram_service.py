"""Telegram Bot API integration for sending notifications and alerts.

Uses the Telegram Bot API to send messages to a configured chat.
Supports plain text and formatted alert messages.
"""

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

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=15.0)
        return self._http_client

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def send_message(self, text: str, parse_mode: str = "HTML") -> dict | None:
        """Send a text message to the configured Telegram chat.

        Args:
            text: Message content (supports HTML formatting)
            parse_mode: Telegram parse mode (HTML or MarkdownV2)

        Returns:
            Telegram API response dict, or None on failure
        """
        if not self.configured:
            logger.warning("Telegram not configured — skipping message")
            return None

        try:
            client = await self._get_http_client()
            url = f"{TELEGRAM_API_BASE}/bot{settings.telegram_bot_token}/sendMessage"
            resp = await client.post(url, json={
                "chat_id": settings.telegram_chat_id,
                "text": text,
                "parse_mode": parse_mode,
            })
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                logger.warning("Telegram API error: %s", data.get("description"))
                return None
            return data
        except Exception as e:
            logger.warning("Telegram send failed: %s", e)
            return None

    async def send_alert(self, alert: dict) -> dict | None:
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
        action = alert.get("suggested_action", "monitor").upper()
        confidence = alert.get("confidence", 0.0)

        text = (
            f"{severity_emoji} <b>ORACLE Alert — {severity}</b>\n\n"
            f"<b>{title}</b>\n"
            f"Symbol: <code>{symbol}</code>\n"
            f"{description}\n\n"
            f"Action: <b>{action}</b> (confidence: {confidence:.0%})"
        )

        return await self.send_message(text)

    async def send_test_message(self) -> dict | None:
        """Send a test message to verify Telegram configuration."""
        return await self.send_message(
            "\u2705 <b>ORACLE Connected</b>\n\n"
            "Telegram notifications are working correctly."
        )

    async def get_bot_info(self) -> dict | None:
        """Get info about the configured bot (for status check)."""
        if not self.configured:
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


# Singleton
telegram_service = TelegramService()
