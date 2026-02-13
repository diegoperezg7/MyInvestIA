"""Notification endpoints for alerts and messaging.

Routes through OpenClaw when enabled, falls back to direct Telegram.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.services.openclaw_service import openclaw_service
from app.services.telegram_service import telegram_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class SendAlertRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(max_length=1000, default="")
    severity: str = Field(default="medium", pattern=r"^(low|medium|high|critical)$")
    asset_symbol: str = Field(default="", max_length=10)
    suggested_action: str = Field(default="monitor", pattern=r"^(buy|sell|wait|monitor)$")
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class NotificationStatus(BaseModel):
    configured: bool
    channel: str = "none"
    bot_name: str | None = None
    bot_username: str | None = None
    openclaw_status: str | None = None


class NotificationResponse(BaseModel):
    success: bool
    message: str
    channel: str = "unknown"


def _get_channel() -> str:
    """Determine which notification channel to use."""
    if openclaw_service.configured:
        return "openclaw"
    if telegram_service.configured:
        return "telegram"
    return "none"


@router.get("/status", response_model=NotificationStatus)
async def get_notification_status():
    """Check notification configuration status."""
    channel = _get_channel()

    if channel == "openclaw":
        oc_health = await openclaw_service.health_check()
        return NotificationStatus(
            configured=True,
            channel="openclaw",
            openclaw_status=oc_health.get("status"),
        )

    if channel == "telegram":
        bot_info = await telegram_service.get_bot_info()
        if bot_info:
            return NotificationStatus(
                configured=True,
                channel="telegram",
                bot_name=bot_info.get("first_name"),
                bot_username=bot_info.get("username"),
            )
        return NotificationStatus(configured=True, channel="telegram")

    return NotificationStatus(configured=False)


@router.post("/send", response_model=NotificationResponse)
async def send_notification(request: SendMessageRequest):
    """Send a message via the configured channel (OpenClaw or Telegram)."""
    channel = _get_channel()

    if channel == "openclaw":
        result = await openclaw_service.wake(request.message)
        if result:
            return NotificationResponse(success=True, message="Sent via OpenClaw", channel="openclaw")
        return NotificationResponse(success=False, message="OpenClaw send failed", channel="openclaw")

    if channel == "telegram":
        result = await telegram_service.send_message(request.message)
        if result:
            return NotificationResponse(success=True, message="Sent via Telegram", channel="telegram")
        return NotificationResponse(success=False, message="Telegram send failed", channel="telegram")

    raise HTTPException(status_code=503, detail="No notification channel configured")


@router.post("/send-alert", response_model=NotificationResponse)
async def send_alert_notification(request: SendAlertRequest):
    """Send a formatted alert via the configured channel."""
    channel = _get_channel()
    alert_dict = request.model_dump()

    if channel == "openclaw":
        result = await openclaw_service.send_alert(alert_dict)
        if result:
            return NotificationResponse(success=True, message="Alert sent via OpenClaw", channel="openclaw")
        return NotificationResponse(success=False, message="OpenClaw alert failed", channel="openclaw")

    if channel == "telegram":
        result = await telegram_service.send_alert(alert_dict)
        if result:
            return NotificationResponse(success=True, message="Alert sent via Telegram", channel="telegram")
        return NotificationResponse(success=False, message="Telegram alert failed", channel="telegram")

    raise HTTPException(status_code=503, detail="No notification channel configured")


@router.post("/test", response_model=NotificationResponse)
async def send_test_notification():
    """Send a test message to verify the active channel."""
    channel = _get_channel()

    if channel == "openclaw":
        result = await openclaw_service.wake(
            "ORACLE test notification — OpenClaw integration is working correctly."
        )
        if result:
            return NotificationResponse(success=True, message="Test sent via OpenClaw", channel="openclaw")
        return NotificationResponse(success=False, message="OpenClaw test failed", channel="openclaw")

    if channel == "telegram":
        result = await telegram_service.send_test_message()
        if result:
            return NotificationResponse(success=True, message="Test sent via Telegram", channel="telegram")
        return NotificationResponse(success=False, message="Telegram test failed", channel="telegram")

    raise HTTPException(status_code=503, detail="No notification channel configured")
