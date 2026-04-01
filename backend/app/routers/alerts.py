from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import AuthUser, get_current_user
from app.schemas.alerting import StructuredAlertList, StructuredScanAndNotifyResponse
from app.schemas.workflow import (
    AlertRuleCreateRequest,
    AlertRuleListResponse,
    AlertRuleUpdateRequest,
    CompoundAlertRule,
)
from app.services.alert_scorer import build_portfolio_alerts, scan_symbols, sort_alerts
from app.services.alerts_engine import scan_and_notify
from app.services.personal_bot_service import personal_bot_service
from app.services.store import store

router = APIRouter(prefix="/alerts", tags=["alerts"])

# Default symbols to scan when no specific symbols requested
DEFAULT_SCAN_SYMBOLS = [
    {"symbol": "AAPL", "type": "stock"},
    {"symbol": "MSFT", "type": "stock"},
    {"symbol": "GOOGL", "type": "stock"},
    {"symbol": "AMZN", "type": "stock"},
    {"symbol": "NVDA", "type": "stock"},
    {"symbol": "TSLA", "type": "stock"},
    {"symbol": "META", "type": "stock"},
    {"symbol": "SPY", "type": "etf"},
    {"symbol": "QQQ", "type": "etf"},
]


def _alert_payload(alert: object) -> dict:
    if hasattr(alert, "model_dump"):
        data = alert.model_dump()
    else:
        data = {
            "id": getattr(alert, "id", ""),
            "type": getattr(getattr(alert, "type", None), "value", "multi_factor"),
            "severity": getattr(getattr(alert, "severity", None), "value", "medium"),
            "title": getattr(alert, "title", "Alert"),
            "description": getattr(alert, "description", ""),
            "reasoning": getattr(alert, "reasoning", ""),
            "confidence": float(getattr(alert, "confidence", 0.0) or 0.0),
            "suggested_action": getattr(getattr(alert, "suggested_action", None), "value", "monitor"),
            "created_at": getattr(alert, "created_at", _iso_now()),
            "asset_symbol": getattr(alert, "asset_symbol", None),
        }
    data.setdefault("reason", data.get("reasoning", ""))
    data.setdefault("evidence", [])
    data.setdefault("sources", [])
    data.setdefault("warnings", [])
    return data


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/", response_model=StructuredAlertList)
async def get_alerts(
    scan: bool = Query(
        default=False, description="Run a live scan on portfolio + watchlist assets"
    ),
    user: AuthUser = Depends(get_current_user),
):
    """Get active alerts.

    By default returns cached/recent alerts. With scan=true, runs a live
    analysis on portfolio holdings and watchlist assets to generate fresh alerts.
    """
    if not scan:
        return StructuredAlertList()

    # Gather symbols from portfolio and watchlists
    symbols_to_scan: list[dict] = []
    seen: set[str] = set()

    # Portfolio holdings
    for holding in store.get_holdings(user.id, user.tenant_id):
        sym = holding["symbol"]
        if sym not in seen:
            symbols_to_scan.append({"symbol": sym, "type": holding["type"]})
            seen.add(sym)

    # Watchlist assets
    for wl in store.get_watchlists(user.id, user.tenant_id):
        for asset in wl.get("assets", []):
            sym = asset["symbol"]
            if sym not in seen:
                symbols_to_scan.append({"symbol": sym, "type": asset["type"]})
                seen.add(sym)

    # If no user assets, scan defaults
    if not symbols_to_scan:
        symbols_to_scan = DEFAULT_SCAN_SYMBOLS

    asset_alerts = await scan_symbols(symbols_to_scan)
    portfolio_alerts = await build_portfolio_alerts(
        store.get_holdings(user.id, user.tenant_id)
    )
    alerts = sort_alerts(asset_alerts + portfolio_alerts)

    return StructuredAlertList(alerts=[_alert_payload(alert) for alert in alerts], total=len(alerts))


@router.get("/scan/{symbol}", response_model=StructuredAlertList)
async def scan_single_asset(symbol: str, user: AuthUser = Depends(get_current_user)):
    """Run alert scan on a single asset and return any alerts."""
    alerts = await scan_symbols([{"symbol": symbol.upper(), "type": "stock"}])
    return StructuredAlertList(alerts=[_alert_payload(alert) for alert in alerts], total=len(alerts))


def _gather_user_symbols(user_id: str, tenant_id: str | None = None) -> list[dict]:
    """Gather symbols from portfolio holdings and watchlists."""
    symbols: list[dict] = []
    seen: set[str] = set()

    for holding in store.get_holdings(user_id, tenant_id):
        sym = holding["symbol"]
        if sym not in seen:
            symbols.append({"symbol": sym, "type": holding["type"]})
            seen.add(sym)

    for wl in store.get_watchlists(user_id, tenant_id):
        for asset in wl.get("assets", []):
            sym = asset["symbol"]
            if sym not in seen:
                symbols.append({"symbol": sym, "type": asset["type"]})
                seen.add(sym)

    return symbols if symbols else DEFAULT_SCAN_SYMBOLS


@router.post("/scan-and-notify", response_model=StructuredScanAndNotifyResponse)
async def scan_and_notify_endpoint(
    min_severity: str = Query(
        default="high",
        description="Minimum alert severity to send via Telegram (all, medium, high, critical)",
    ),
    user: AuthUser = Depends(get_current_user),
):
    """Scan portfolio and watchlist assets, then send qualifying alerts via Telegram.

    Combines the alert scanner with Telegram delivery. Only alerts meeting
    the min_severity threshold are sent as notifications.
    """
    symbols = _gather_user_symbols(user.id, user.tenant_id)
    personal_chat_id = personal_bot_service.get_connected_chat_id(
        user.id,
        user.tenant_id,
    )
    result = await scan_and_notify(
        symbols,
        min_severity=min_severity,
        chat_id=personal_chat_id,
        portfolio_holdings=store.get_holdings(user.id, user.tenant_id),
    )

    return StructuredScanAndNotifyResponse(
        alerts=[_alert_payload(alert) for alert in result["alerts"]],
        notified=[
            {
                "alert_id": n["alert_id"],
                "symbol": n["symbol"],
                "title": n["title"],
                "severity": n["severity"],
                "delivered": n["delivered"],
                "sources": n.get("sources", []),
            }
            for n in result["notified"]
        ],
        total_alerts=result["total_alerts"],
        total_notified=result["total_notified"],
        telegram_configured=result["telegram_configured"],
    )


@router.get("/rules", response_model=AlertRuleListResponse)
async def get_alert_rules(user: AuthUser = Depends(get_current_user)):
    rules = store.get_alert_rules(user.id, user.tenant_id)
    return AlertRuleListResponse(
        rules=[CompoundAlertRule(**rule) for rule in rules],
        total=len(rules),
    )


@router.post("/rules", response_model=CompoundAlertRule)
async def create_alert_rule(
    request: AlertRuleCreateRequest,
    user: AuthUser = Depends(get_current_user),
):
    now = _iso_now()
    rule = store.create_alert_rule(
        user.id,
        {
            **request.model_dump(),
            "created_at": now,
            "updated_at": now,
        },
        user.tenant_id,
    )
    return CompoundAlertRule(**rule)


@router.patch("/rules/{rule_id}", response_model=CompoundAlertRule)
async def patch_alert_rule(
    rule_id: str,
    request: AlertRuleUpdateRequest,
    user: AuthUser = Depends(get_current_user),
):
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    updates["updated_at"] = _iso_now()
    rule = store.update_alert_rule(user.id, rule_id, updates, user.tenant_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return CompoundAlertRule(**rule)
