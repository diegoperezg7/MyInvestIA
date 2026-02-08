"""Notification endpoints for Telegram alerts and messaging."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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
    bot_name: str | None = None
    bot_username: str | None = None
    chat_id: str | None = None


class NotificationResponse(BaseModel):
    success: bool
    message: str


@router.get("/status", response_model=NotificationStatus)
async def get_notification_status():
    """Check if Telegram notifications are configured and working."""
    if not telegram_service.configured:
        return NotificationStatus(configured=False)

    bot_info = await telegram_service.get_bot_info()
    if bot_info:
        return NotificationStatus(
            configured=True,
            bot_name=bot_info.get("first_name"),
            bot_username=bot_info.get("username"),
            chat_id="configured",
        )
    return NotificationStatus(configured=True, chat_id="configured")


@router.post("/send", response_model=NotificationResponse)
async def send_notification(request: SendMessageRequest):
    """Send a custom message via Telegram."""
    if not telegram_service.configured:
        raise HTTPException(status_code=503, detail="Telegram not configured")

    result = await telegram_service.send_message(request.message)
    if result:
        return NotificationResponse(success=True, message="Message sent successfully")
    return NotificationResponse(success=False, message="Failed to send message")


@router.post("/send-alert", response_model=NotificationResponse)
async def send_alert_notification(request: SendAlertRequest):
    """Send a formatted alert notification via Telegram."""
    if not telegram_service.configured:
        raise HTTPException(status_code=503, detail="Telegram not configured")

    alert_dict = {
        "title": request.title,
        "description": request.description,
        "severity": request.severity,
        "asset_symbol": request.asset_symbol,
        "suggested_action": request.suggested_action,
        "confidence": request.confidence,
    }
    result = await telegram_service.send_alert(alert_dict)
    if result:
        return NotificationResponse(success=True, message="Alert sent successfully")
    return NotificationResponse(success=False, message="Failed to send alert")


@router.post("/test", response_model=NotificationResponse)
async def send_test_notification():
    """Send a test message to verify Telegram is working."""
    if not telegram_service.configured:
        raise HTTPException(status_code=503, detail="Telegram not configured")

    result = await telegram_service.send_test_message()
    if result:
        return NotificationResponse(success=True, message="Test message sent")
    return NotificationResponse(success=False, message="Test message failed")
