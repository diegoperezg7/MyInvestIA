import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response

from app.dependencies import AuthUser, get_current_user
from app.schemas.asset import (
    AddHoldingRequest,
    Asset,
    Portfolio,
    PortfolioHolding,
    PortfolioRiskResponse,
    UpdateHoldingRequest,
)
from app.services.csv_service import export_portfolio_csv, parse_portfolio_csv
from app.services.currency_service import convert_currency
from app.services.dividend_service import get_portfolio_dividends
from app.services.market_data import market_data_service
from app.services.store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

# Base currency for portfolio P&L calculations
PORTFOLIO_BASE_CURRENCY = "EUR"

# Cache for FX rates within a single request cycle
_fx_cache: dict[str, float] = {}


async def _get_fx_rate(from_currency: str, to_currency: str) -> float:
    """Get FX rate with in-memory caching for the request."""
    if from_currency == to_currency:
        return 1.0
    key = f"{from_currency}:{to_currency}"
    if key in _fx_cache:
        return _fx_cache[key]
    result = await convert_currency(1.0, from_currency, to_currency)
    rate = result["rate"] if result else 1.0
    _fx_cache[key] = rate
    return rate


async def _build_holding(h: dict) -> PortfolioHolding:
    """Convert a store holding dict into a PortfolioHolding with live market data."""
    quote = await market_data_service.get_quote(h["symbol"], h["type"])

    if quote:
        raw_price = quote["price"]
        change_percent = quote["change_percent"]
        volume = quote["volume"]
        quote_currency = quote.get("currency", "USD")
    else:
        # Fallback to cost basis if market data unavailable
        raw_price = h["avg_buy_price"]
        change_percent = 0.0
        volume = 0.0
        quote_currency = PORTFOLIO_BASE_CURRENCY  # assume same currency

    # Convert price to portfolio base currency (EUR) if needed
    fx_rate = await _get_fx_rate(quote_currency, PORTFOLIO_BASE_CURRENCY)
    price = raw_price * fx_rate

    asset = Asset(
        symbol=h["symbol"],
        name=h["name"],
        type=h["type"],
        price=round(price, 4),
        change_percent=change_percent,
        volume=volume,
    )
    current_value = h["quantity"] * price
    cost_basis = h["quantity"] * h["avg_buy_price"]
    unrealized_pnl = current_value - cost_basis
    unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0.0

    return PortfolioHolding(
        asset=asset,
        quantity=h["quantity"],
        avg_buy_price=h["avg_buy_price"],
        current_value=round(current_value, 2),
        unrealized_pnl=round(unrealized_pnl, 2),
        unrealized_pnl_percent=round(unrealized_pnl_pct, 2),
        source=h.get("source", "manual"),
        connection_id=h.get("connection_id"),
    )


@router.get("/risk", response_model=PortfolioRiskResponse)
async def get_portfolio_risk(user: AuthUser = Depends(get_current_user)):
    """Get portfolio risk analytics (VaR, Sharpe, correlation, stress tests)."""
    from app.services.portfolio_risk import calculate_portfolio_risk

    raw_holdings = store.get_holdings(user.id, user.tenant_id)
    if not raw_holdings:
        return PortfolioRiskResponse()

    built = list(await asyncio.gather(*[_build_holding(h) for h in raw_holdings]))
    holdings_for_risk = [
        {
            "symbol": h.asset.symbol,
            "quantity": h.quantity,
            "current_value": h.current_value,
        }
        for h in built
        if h.current_value > 0
    ]

    result = await calculate_portfolio_risk(holdings_for_risk)
    return PortfolioRiskResponse(**result)


@router.get("/", response_model=Portfolio)
async def get_portfolio(
    source: str | None = None, user: AuthUser = Depends(get_current_user)
):
    """Get the full portfolio with all holdings and live prices.

    Optional source filter: manual, exchange, wallet, broker, prediction
    """
    raw_holdings = store.get_holdings(user.id, user.tenant_id)
    if source:
        raw_holdings = [h for h in raw_holdings if h.get("source", "manual") == source]
    holdings = list(await asyncio.gather(*[_build_holding(h) for h in raw_holdings]))
    total_value = sum(h.current_value for h in holdings)
    daily_pnl = sum(
        h.current_value * h.asset.change_percent / 100.0
        for h in holdings
        if h.asset.change_percent != 0.0
    )
    daily_pnl_pct = (daily_pnl / total_value * 100) if total_value > 0 else 0.0

    return Portfolio(
        total_value=round(total_value, 2),
        daily_pnl=round(daily_pnl, 2),
        daily_pnl_percent=round(daily_pnl_pct, 2),
        holdings=holdings,
    )


@router.get("/{symbol}", response_model=PortfolioHolding)
async def get_holding(symbol: str, user: AuthUser = Depends(get_current_user)):
    """Get a single holding by symbol."""
    raw = store.get_holding(user.id, symbol, user.tenant_id)
    if not raw:
        raise HTTPException(
            status_code=404, detail=f"Holding '{symbol.upper()}' not found"
        )
    return await _build_holding(raw)


@router.post("/", response_model=PortfolioHolding, status_code=201)
async def add_holding(
    req: AddHoldingRequest, user: AuthUser = Depends(get_current_user)
):
    """Add a new holding or average into an existing one."""
    raw = store.add_holding(
        user_id=user.id,
        symbol=req.symbol,
        name=req.name,
        asset_type=req.type.value,
        quantity=req.quantity,
        avg_buy_price=req.avg_buy_price,
        tenant_id=user.tenant_id,
    )
    return await _build_holding(raw)


@router.patch("/{symbol}", response_model=PortfolioHolding)
async def update_holding(
    symbol: str, req: UpdateHoldingRequest, user: AuthUser = Depends(get_current_user)
):
    """Update quantity or average buy price for a holding."""
    if req.quantity is None and req.avg_buy_price is None:
        raise HTTPException(
            status_code=400, detail="At least one field must be provided"
        )
    raw = store.update_holding(
        user.id,
        symbol,
        quantity=req.quantity,
        avg_buy_price=req.avg_buy_price,
        tenant_id=user.tenant_id,
    )
    if not raw:
        raise HTTPException(
            status_code=404, detail=f"Holding '{symbol.upper()}' not found"
        )
    return await _build_holding(raw)


@router.delete("/{symbol}", status_code=204)
async def delete_holding(symbol: str, user: AuthUser = Depends(get_current_user)):
    """Remove a manual holding from the portfolio. Synced holdings cannot be deleted here."""
    raw = store.get_holding(user.id, symbol, user.tenant_id)
    if not raw:
        raise HTTPException(
            status_code=404, detail=f"Holding '{symbol.upper()}' not found"
        )
    if raw.get("source", "manual") != "manual":
        raise HTTPException(
            status_code=400,
            detail=f"Holding '{symbol.upper()}' is synced from an external connection. "
            "Delete the connection to remove its holdings.",
        )
    if not store.delete_holding(user.id, symbol, user.tenant_id):
        raise HTTPException(
            status_code=404, detail=f"Holding '{symbol.upper()}' not found"
        )


@router.get("/export", response_class=Response)
async def export_csv(user: AuthUser = Depends(get_current_user)):
    """Export portfolio holdings as CSV."""
    raw_holdings = store.get_holdings(user.id, user.tenant_id)
    built = list(await asyncio.gather(*[_build_holding(h) for h in raw_holdings]))
    holdings_data = [
        {
            "asset": {
                "symbol": holding.asset.symbol,
                "name": holding.asset.name,
                "type": holding.asset.type.value,
            },
            "quantity": holding.quantity,
            "avg_buy_price": holding.avg_buy_price,
            "current_value": holding.current_value,
            "unrealized_pnl": holding.unrealized_pnl,
        }
        for holding in built
    ]

    csv_content = export_portfolio_csv(holdings_data)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=portfolio.csv"},
    )


@router.post("/import")
async def import_csv(
    file: UploadFile = File(...), user: AuthUser = Depends(get_current_user)
):
    """Import portfolio holdings from CSV."""
    content = (await file.read()).decode("utf-8")
    holdings = parse_portfolio_csv(content)

    imported = []
    for h in holdings:
        try:
            raw = store.add_holding(
                user_id=user.id,
                symbol=h["symbol"],
                name=h.get("name", h["symbol"]),
                asset_type=h.get("type", "stock"),
                quantity=h["quantity"],
                avg_buy_price=h["avg_buy_price"],
                tenant_id=user.tenant_id,
            )
            imported.append(raw["symbol"])
        except Exception:
            pass

    return {"imported": len(imported), "symbols": imported}


@router.get("/dividends")
async def get_dividends(user: AuthUser = Depends(get_current_user)):
    """Get dividend data for all portfolio holdings."""
    raw_holdings = store.get_holdings(user.id, user.tenant_id)
    symbols = [h["symbol"] for h in raw_holdings]
    if not symbols:
        return {"dividends": {}, "total_annual": 0, "symbols_with_dividends": 0}
    return get_portfolio_dividends(symbols)
