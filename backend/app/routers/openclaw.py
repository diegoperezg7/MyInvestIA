"""OpenClaw integration router.

Provides endpoints for:
- OpenClaw status and health checks
- Triggering alerts/summaries through OpenClaw
- Callback webhook for OpenClaw to query MyInvestIA data
- Portfolio Q&A via OpenClaw (Telegram chat)

NO AUTH REQUIRED — OpenClaw is a server-side integration, not a user-facing app.
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


@router.get("/status")
async def get_openclaw_status():
    """Check OpenClaw connection status."""
    return await openclaw_service.health_check()


@router.post("/send-alert", response_model=OpenClawResponse)
async def send_alert_via_openclaw(req: OpenClawAlertRequest):
    """Send an investment alert through OpenClaw."""
    if not openclaw_service.configured:
        raise HTTPException(status_code=503, detail="OpenClaw not configured")
    result = await openclaw_service.send_alert(req.model_dump())
    if result:
        return OpenClawResponse(
            success=True, message="Alert sent to OpenClaw", data=result
        )
    return OpenClawResponse(success=False, message="Failed to send alert to OpenClaw")


@router.post("/wake", response_model=OpenClawResponse)
async def wake_openclaw(req: OpenClawMessage):
    """Send a wake event to OpenClaw."""
    if not openclaw_service.configured:
        raise HTTPException(status_code=503, detail="OpenClaw not configured")
    result = await openclaw_service.wake(req.message)
    if result:
        return OpenClawResponse(success=True, message="Wake event sent", data=result)
    return OpenClawResponse(success=False, message="Failed to send wake event")


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
        return OpenClawResponse(
            success=True, message="Market summary sent to OpenClaw", data=result
        )
    return OpenClawResponse(success=False, message="Failed to send market summary")


@router.post("/portfolio-update", response_model=OpenClawResponse)
async def send_portfolio_update():
    """Send current portfolio status through OpenClaw (no auth — server-side)."""
    if not openclaw_service.configured:
        raise HTTPException(status_code=503, detail="OpenClaw not configured")
    return OpenClawResponse(
        success=True, message="No holdings to report (multi-user: use user endpoint)"
    )


@router.post("/scan-alerts", response_model=OpenClawResponse)
async def scan_and_send_alerts():
    """Run alert scan and send results through OpenClaw."""
    if not openclaw_service.configured:
        raise HTTPException(status_code=503, detail="OpenClaw not configured")
    return OpenClawResponse(
        success=True, message="No symbols to scan (multi-user: use user endpoint)"
    )


@router.post("/ask", response_model=OpenClawResponse)
async def ask_portfolio_question(req: OpenClawMessage):
    """Ask a question about the portfolio via OpenClaw."""
    if not openclaw_service.configured:
        raise HTTPException(status_code=503, detail="OpenClaw not configured")
    result = await openclaw_service.query_portfolio(req.message)
    if result:
        return OpenClawResponse(
            success=True, message="Question sent to OpenClaw", data=result
        )
    return OpenClawResponse(success=False, message="Failed to send question")


@router.post("/callback")
async def openclaw_callback(request: Request):
    """Webhook endpoint for OpenClaw to call back to MyInvestIA."""
    body = await request.json()
    action = body.get("action", "snapshot")

    if action == "snapshot":
        from app.services.macro_intelligence import get_all_macro_indicators

        return {
            "portfolio": {"holdings": []},
            "watchlists": [],
            "macro": await get_all_macro_indicators(),
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
        records = await market_data_service.get_history(
            symbol, period="6mo", interval="1d"
        )
        if records and len(records) >= 30:
            closes = [r["close"] for r in records]
            indicators = compute_all_indicators(closes)
            return {"symbol": symbol, "indicators": indicators}
        return {"symbol": symbol, "error": "Insufficient data"}

    return {"error": f"Unknown action: {action}"}


# Public endpoints for OpenClaw skill (no auth required)
@router.get("/public/quote/{symbol}")
async def public_quote(symbol: str):
    """Public endpoint for getting quotes without authentication."""
    from app.services.market_data import market_data_service

    quote = await market_data_service.get_quote(symbol.upper())
    return quote or {"error": f"No data for {symbol}", "symbol": symbol.upper()}


@router.get("/public/macro")
async def public_macro():
    """Public endpoint for macro indicators without authentication."""
    from app.services.macro_intelligence import get_all_macro_indicators

    return await get_all_macro_indicators()
