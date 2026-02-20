from fastapi import APIRouter, Depends, Query

from app.dependencies import AuthUser, get_current_user
from app.schemas.asset import AlertList, ScanAndNotifyResponse
from app.services.alert_scorer import scan_symbols
from app.services.alerts_engine import scan_and_notify
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


@router.get("/", response_model=AlertList)
async def get_alerts(
    scan: bool = Query(default=False, description="Run a live scan on portfolio + watchlist assets"),
    user: AuthUser = Depends(get_current_user),
):
    """Get active alerts.

    By default returns cached/recent alerts. With scan=true, runs a live
    analysis on portfolio holdings and watchlist assets to generate fresh alerts.
    """
    if not scan:
        return AlertList()

    # Gather symbols from portfolio and watchlists
    symbols_to_scan: list[dict] = []
    seen: set[str] = set()

    # Portfolio holdings
    for holding in store.get_holdings(user.id):
        sym = holding["symbol"]
        if sym not in seen:
            symbols_to_scan.append({"symbol": sym, "type": holding["type"]})
            seen.add(sym)

    # Watchlist assets
    for wl in store.get_watchlists(user.id):
        for asset in wl.get("assets", []):
            sym = asset["symbol"]
            if sym not in seen:
                symbols_to_scan.append({"symbol": sym, "type": asset["type"]})
                seen.add(sym)

    # If no user assets, scan defaults
    if not symbols_to_scan:
        symbols_to_scan = DEFAULT_SCAN_SYMBOLS

    alerts = await scan_symbols(symbols_to_scan)

    return AlertList(alerts=alerts, total=len(alerts))


@router.get("/scan/{symbol}", response_model=AlertList)
async def scan_single_asset(symbol: str, user: AuthUser = Depends(get_current_user)):
    """Run alert scan on a single asset and return any alerts."""
    alerts = await scan_symbols([{"symbol": symbol.upper(), "type": "stock"}])
    return AlertList(alerts=alerts, total=len(alerts))


def _gather_user_symbols(user_id: str) -> list[dict]:
    """Gather symbols from portfolio holdings and watchlists."""
    symbols: list[dict] = []
    seen: set[str] = set()

    for holding in store.get_holdings(user_id):
        sym = holding["symbol"]
        if sym not in seen:
            symbols.append({"symbol": sym, "type": holding["type"]})
            seen.add(sym)

    for wl in store.get_watchlists(user_id):
        for asset in wl.get("assets", []):
            sym = asset["symbol"]
            if sym not in seen:
                symbols.append({"symbol": sym, "type": asset["type"]})
                seen.add(sym)

    return symbols if symbols else DEFAULT_SCAN_SYMBOLS


@router.post("/scan-and-notify", response_model=ScanAndNotifyResponse)
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
    symbols = _gather_user_symbols(user.id)
    result = await scan_and_notify(symbols, min_severity=min_severity)

    return ScanAndNotifyResponse(
        alerts=result["alerts"],
        notified=[
            {"alert_id": n["alert_id"], "symbol": n["symbol"],
             "title": n["title"], "severity": n["severity"],
             "delivered": n["delivered"]}
            for n in result["notified"]
        ],
        total_alerts=result["total_alerts"],
        total_notified=result["total_notified"],
        telegram_configured=result["telegram_configured"],
    )
