"""OpenClaw integration router.

Provides endpoints for:
- OpenClaw status and health checks
- Triggering alerts/summaries through OpenClaw
- Callback webhook for OpenClaw to query MyInvestIA data
- Portfolio Q&A via OpenClaw (Telegram chat)
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.openclaw_service import openclaw_service

router = APIRouter(prefix="/openclaw", tags=["openclaw"])


class OpenClawMessage(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class OpenClawAlertRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(max_length=1000, default="")
    severity: str = Field(default="medium", pattern=r"^(low|medium|high|critical)$")
    asset_symbol: str = Field(default="", max_length=10)
    suggested_action: str = Field(default="monitor")
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    reasoning: str = Field(default="", max_length=2000)


class OpenClawResponse(BaseModel):
    success: bool
    message: str
    data: dict | None = None


# --- Status ---

@router.get("/status")
async def get_openclaw_status():
    """Check OpenClaw connection status."""
    return await openclaw_service.health_check()


# --- Send alerts through OpenClaw ---

@router.post("/send-alert", response_model=OpenClawResponse)
async def send_alert_via_openclaw(req: OpenClawAlertRequest):
    """Send an investment alert through OpenClaw (delivers to Telegram with AI commentary)."""
    if not openclaw_service.configured:
        raise HTTPException(status_code=503, detail="OpenClaw not configured")

    result = await openclaw_service.send_alert(req.model_dump())
    if result:
        return OpenClawResponse(success=True, message="Alert sent to OpenClaw", data=result)
    return OpenClawResponse(success=False, message="Failed to send alert to OpenClaw")


@router.post("/wake", response_model=OpenClawResponse)
async def wake_openclaw(req: OpenClawMessage):
    """Send a wake event to OpenClaw (simple notification to Telegram)."""
    if not openclaw_service.configured:
        raise HTTPException(status_code=503, detail="OpenClaw not configured")

    result = await openclaw_service.wake(req.message)
    if result:
        return OpenClawResponse(success=True, message="Wake event sent", data=result)
    return OpenClawResponse(success=False, message="Failed to send wake event")


# --- Market summary ---

@router.post("/market-summary", response_model=OpenClawResponse)
async def send_market_summary():
    """Generate and send a market summary through OpenClaw."""
    if not openclaw_service.configured:
        raise HTTPException(status_code=503, detail="OpenClaw not configured")

    from app.services.market_data import market_data_service
    from app.services.macro_intelligence import get_all_macro_indicators

    movers = await market_data_service.get_top_movers()
    macro = await get_all_macro_indicators()

    summary_data = {
        "gainers": movers.get("gainers", []),
        "losers": movers.get("losers", []),
        "macro": macro,
    }

    result = await openclaw_service.send_market_summary(summary_data)
    if result:
        return OpenClawResponse(success=True, message="Market summary sent to OpenClaw", data=result)
    return OpenClawResponse(success=False, message="Failed to send market summary")


# --- Portfolio update ---

@router.post("/portfolio-update", response_model=OpenClawResponse)
async def send_portfolio_update():
    """Send current portfolio status through OpenClaw."""
    if not openclaw_service.configured:
        raise HTTPException(status_code=503, detail="OpenClaw not configured")

    from app.services.market_data import market_data_service
    from app.services.store import store

    raw_holdings = store.get_holdings()
    if not raw_holdings:
        return OpenClawResponse(success=True, message="No holdings to report")

    # Build portfolio summary
    import asyncio
    from app.routers.portfolio import _build_holding

    holdings = list(await asyncio.gather(*[_build_holding(h) for h in raw_holdings]))
    total_value = sum(h.current_value for h in holdings)
    daily_pnl = sum(
        h.current_value * h.asset.change_percent / 100.0
        for h in holdings
        if h.asset.change_percent != 0.0
    )
    daily_pnl_pct = (daily_pnl / total_value * 100) if total_value > 0 else 0.0

    portfolio_data = {
        "total_value": total_value,
        "daily_pnl": daily_pnl,
        "daily_pnl_percent": daily_pnl_pct,
        "holdings": [
            {
                "asset": {"symbol": h.asset.symbol, "change_percent": h.asset.change_percent},
                "current_value": h.current_value,
                "unrealized_pnl": h.unrealized_pnl,
            }
            for h in holdings
        ],
    }

    result = await openclaw_service.send_portfolio_update(portfolio_data)
    if result:
        return OpenClawResponse(success=True, message="Portfolio update sent", data=result)
    return OpenClawResponse(success=False, message="Failed to send portfolio update")


# --- Scan & send alerts ---

@router.post("/scan-alerts", response_model=OpenClawResponse)
async def scan_and_send_alerts():
    """Run alert scan on portfolio + watchlist and send results through OpenClaw."""
    if not openclaw_service.configured:
        raise HTTPException(status_code=503, detail="OpenClaw not configured")

    from app.services.alert_scorer import scan_symbols
    from app.services.store import store

    # Gather symbols from portfolio and watchlists
    symbols = []
    for h in store.get_holdings():
        symbols.append({"symbol": h["symbol"], "type": h.get("type", "stock")})
    for wl in store.get_watchlists():
        for a in wl.get("assets", []):
            if not any(s["symbol"] == a["symbol"] for s in symbols):
                symbols.append({"symbol": a["symbol"], "type": a.get("type", "stock")})

    if not symbols:
        return OpenClawResponse(success=True, message="No symbols to scan")

    alerts = await scan_symbols(symbols)

    if not alerts:
        return OpenClawResponse(success=True, message="No alerts generated")

    # Send each high/critical alert through OpenClaw
    sent = 0
    for alert in alerts:
        if alert.severity.value in ("high", "critical"):
            result = await openclaw_service.send_alert({
                "title": alert.title,
                "description": alert.description,
                "severity": alert.severity.value,
                "asset_symbol": alert.asset_symbol or "",
                "suggested_action": alert.suggested_action.value,
                "confidence": alert.confidence,
                "reasoning": alert.reasoning,
            })
            if result:
                sent += 1

    return OpenClawResponse(
        success=True,
        message=f"Scanned {len(symbols)} symbols, {len(alerts)} alerts found, {sent} sent to OpenClaw",
        data={"total_alerts": len(alerts), "sent": sent},
    )


# --- Portfolio Q&A (Telegram chat) ---

@router.post("/ask", response_model=OpenClawResponse)
async def ask_portfolio_question(req: OpenClawMessage):
    """Ask a question about the portfolio via OpenClaw (enables Telegram chat)."""
    if not openclaw_service.configured:
        raise HTTPException(status_code=503, detail="OpenClaw not configured")

    result = await openclaw_service.query_portfolio(req.message)
    if result:
        return OpenClawResponse(success=True, message="Question sent to OpenClaw", data=result)
    return OpenClawResponse(success=False, message="Failed to send question")


# --- Callback endpoint for OpenClaw to query MyInvestIA ---

@router.post("/callback")
async def openclaw_callback(request: Request):
    """Webhook endpoint for OpenClaw to call back to MyInvestIA.

    OpenClaw can POST here to fetch aggregated data for its analysis.
    Returns a snapshot of portfolio, alerts, and market conditions.
    """
    body = await request.json()
    action = body.get("action", "snapshot")

    if action == "snapshot":
        from app.services.market_data import market_data_service
        from app.services.macro_intelligence import get_all_macro_indicators
        from app.services.store import store
        import asyncio

        holdings = store.get_holdings()
        watchlists = store.get_watchlists()
        macro = await get_all_macro_indicators()

        # Get quotes for portfolio symbols
        portfolio_symbols = [h["symbol"] for h in holdings]
        quotes = {}
        if portfolio_symbols:
            tasks = [market_data_service.get_quote(s) for s in portfolio_symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for s, r in zip(portfolio_symbols, results):
                if isinstance(r, dict):
                    quotes[s] = r

        return {
            "portfolio": {
                "holdings": [
                    {
                        "symbol": h["symbol"],
                        "type": h.get("type"),
                        "quantity": h["quantity"],
                        "avg_buy_price": h["avg_buy_price"],
                        "current_price": quotes.get(h["symbol"], {}).get("price"),
                        "change_percent": quotes.get(h["symbol"], {}).get("change_percent"),
                    }
                    for h in holdings
                ],
            },
            "watchlists": [
                {"name": wl["name"], "symbols": [a["symbol"] for a in wl.get("assets", [])]}
                for wl in watchlists
            ],
            "macro": macro,
        }

    elif action == "quote":
        from app.services.market_data import market_data_service
        symbol = body.get("symbol", "")
        if not symbol:
            raise HTTPException(status_code=400, detail="Symbol required")
        quote = await market_data_service.get_quote(symbol)
        return quote or {"error": f"No data for {symbol}"}

    elif action == "analysis":
        from app.services.market_data import market_data_service
        from app.services.technical_analysis import compute_all_indicators
        symbol = body.get("symbol", "").upper()
        if not symbol:
            raise HTTPException(status_code=400, detail="Symbol required")
        records = await market_data_service.get_history(symbol, period="6mo", interval="1d")
        if records and len(records) >= 30:
            closes = [r["close"] for r in records]
            indicators = compute_all_indicators(closes)
            return {"symbol": symbol, "indicators": indicators}
        return {"symbol": symbol, "error": "Insufficient data"}

    return {"error": f"Unknown action: {action}"}
