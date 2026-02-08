from fastapi import APIRouter, Query

from app.schemas.asset import AlertList
from app.services.alert_scorer import scan_symbols
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
    for holding in store.get_holdings():
        sym = holding["symbol"]
        if sym not in seen:
            symbols_to_scan.append({"symbol": sym, "type": holding["type"]})
            seen.add(sym)

    # Watchlist assets
    for wl in store.get_watchlists():
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
async def scan_single_asset(symbol: str):
    """Run alert scan on a single asset and return any alerts."""
    alerts = await scan_symbols([{"symbol": symbol.upper(), "type": "stock"}])
    return AlertList(alerts=alerts, total=len(alerts))
