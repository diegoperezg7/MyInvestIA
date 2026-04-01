"""Notification endpoints for alerts, messaging, and personal Telegram bot flows."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import settings
from app.dependencies import AuthUser, get_current_user
from app.services.openclaw_service import openclaw_service
from app.services.personal_bot_service import personal_bot_service
from app.services.telegram_service import telegram_service

router = APIRouter(prefix="/notifications", tags=["notifications"], dependencies=[Depends(get_current_user)])


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


class PersonalBotHistoryEntry(BaseModel):
    id: str
    connection_id: str
    started_at: str | None = None
    completed_at: str | None = None
    status: str
    reason: str | None = None
    summary: str | None = None
    message_count: int = 0
    alert_count: int = 0
    fingerprint: str | None = None


class PersonalBotStatus(BaseModel):
    available: bool
    enabled: bool
    connected: bool
    status: str
    bot_name: str | None = None
    bot_username: str | None = None
    chat_id: str | None = None
    chat_name: str | None = None
    telegram_username: str | None = None
    cadence_minutes: int = 30
    min_severity: str = "high"
    include_briefing: bool = True
    include_inbox: bool = True
    include_portfolio: bool = True
    include_watchlist: bool = True
    include_macro: bool = True
    include_news: bool = True
    include_theses: bool = True
    include_buy_sell: bool = True
    send_only_on_changes: bool = True
    provisioned_defaults: bool = False
    pending_code: str | None = None
    pending_expires_at: str | None = None
    connect_url: str | None = None
    verified_at: str | None = None
    last_run_at: str | None = None
    last_delivery_at: str | None = None
    last_test_at: str | None = None
    last_error: str | None = None
    last_reason: str | None = None
    last_message_count: int = 0
    last_alert_count: int = 0
    history: list[PersonalBotHistoryEntry] = []


class PersonalBotConfigPatch(BaseModel):
    enabled: bool | None = None
    cadence_minutes: int | None = Field(default=None, ge=5, le=1440)
    min_severity: str | None = Field(
        default=None,
        pattern=r"^(all|medium|high|critical)$",
    )
    include_briefing: bool | None = None
    include_inbox: bool | None = None
    include_portfolio: bool | None = None
    include_watchlist: bool | None = None
    include_macro: bool | None = None
    include_news: bool | None = None
    include_theses: bool | None = None
    include_buy_sell: bool | None = None
    send_only_on_changes: bool | None = None


class PersonalBotActionResponse(BaseModel):
    success: bool
    message: str
    status: PersonalBotStatus


class PersonalBotRunResponse(BaseModel):
    success: bool
    message: str
    sent_messages: int = 0
    sent_alerts: int = 0
    alerts_generated: int = 0
    top_items: int = 0
    events: int = 0
    thesis_watch: int = 0
    skipped: bool = False
    status: PersonalBotStatus


class PersonalBotProvisionResponse(BaseModel):
    success: bool
    created_rules: int
    message: str
    status: PersonalBotStatus


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
            "MyInvestIA test notification — OpenClaw integration is working correctly."
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


@router.get("/bot/status", response_model=PersonalBotStatus)
async def get_personal_bot_status(user: AuthUser = Depends(get_current_user)):
    status = await personal_bot_service.get_status(user.id, user.tenant_id)
    return PersonalBotStatus(**status)


@router.post("/bot/connect", response_model=PersonalBotStatus)
async def start_personal_bot_connect(user: AuthUser = Depends(get_current_user)):
    try:
        status = await personal_bot_service.start_connect(user.id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return PersonalBotStatus(**status)


@router.post("/bot/verify", response_model=PersonalBotActionResponse)
async def verify_personal_bot(user: AuthUser = Depends(get_current_user)):
    try:
        status = await personal_bot_service.verify_connect(user.id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PersonalBotActionResponse(
        success=True,
        message="Bot conectado correctamente",
        status=PersonalBotStatus(**status),
    )


@router.patch("/bot/config", response_model=PersonalBotStatus)
async def patch_personal_bot_config(
    request: PersonalBotConfigPatch,
    user: AuthUser = Depends(get_current_user),
):
    status = await personal_bot_service.update_config(
        user.id,
        {k: v for k, v in request.model_dump().items() if v is not None},
        user.tenant_id,
    )
    return PersonalBotStatus(**status)


@router.post("/bot/disconnect", response_model=PersonalBotActionResponse)
async def disconnect_personal_bot(user: AuthUser = Depends(get_current_user)):
    status = await personal_bot_service.disconnect(user.id, user.tenant_id)
    return PersonalBotActionResponse(
        success=True,
        message="Bot desconectado",
        status=PersonalBotStatus(**status),
    )


@router.post("/bot/test", response_model=PersonalBotActionResponse)
async def test_personal_bot(user: AuthUser = Depends(get_current_user)):
    try:
        result = await personal_bot_service.send_test(user.id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PersonalBotActionResponse(
        success=result["success"],
        message=result["message"],
        status=PersonalBotStatus(**result["status"]),
    )


@router.post("/bot/run", response_model=PersonalBotRunResponse)
async def run_personal_bot(user: AuthUser = Depends(get_current_user)):
    try:
        result = await personal_bot_service.run_now(user.id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    status = await personal_bot_service.get_status(user.id, user.tenant_id)
    return PersonalBotRunResponse(**result, status=PersonalBotStatus(**status))


@router.post("/bot/provision-defaults", response_model=PersonalBotProvisionResponse)
async def provision_personal_bot_defaults(user: AuthUser = Depends(get_current_user)):
    result = await personal_bot_service.provision_default_rules(user.id, user.tenant_id)
    return PersonalBotProvisionResponse(**result)


@router.get("/bot/history", response_model=list[PersonalBotHistoryEntry])
async def get_personal_bot_history(
    limit: int = Query(default=20, ge=1, le=100),
    user: AuthUser = Depends(get_current_user),
):
    history = personal_bot_service.get_history(user.id, user.tenant_id, limit=limit)
    return [PersonalBotHistoryEntry(**entry) for entry in history]
