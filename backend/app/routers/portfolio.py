import asyncio

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response

from app.schemas.asset import (
    AddHoldingRequest,
    Asset,
    Portfolio,
    PortfolioHolding,
    UpdateHoldingRequest,
)
from app.services.csv_service import export_portfolio_csv, parse_portfolio_csv
from app.services.dividend_service import get_portfolio_dividends
from app.services.market_data import market_data_service
from app.services.store import store

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


async def _build_holding(h: dict) -> PortfolioHolding:
    """Convert a store holding dict into a PortfolioHolding with live market data."""
    quote = await market_data_service.get_quote(h["symbol"], h["type"])

    if quote:
        price = quote["price"]
        change_percent = quote["change_percent"]
        volume = quote["volume"]
    else:
        # Fallback to cost basis if market data unavailable
        price = h["avg_buy_price"]
        change_percent = 0.0
        volume = 0.0

    asset = Asset(
        symbol=h["symbol"],
        name=h["name"],
        type=h["type"],
        price=price,
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
    )


@router.get("/", response_model=Portfolio)
async def get_portfolio():
    """Get the full portfolio with all holdings and live prices."""
    raw_holdings = store.get_holdings()
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
async def get_holding(symbol: str):
    """Get a single holding by symbol."""
    raw = store.get_holding(symbol)
    if not raw:
        raise HTTPException(status_code=404, detail=f"Holding '{symbol.upper()}' not found")
    return await _build_holding(raw)


@router.post("/", response_model=PortfolioHolding, status_code=201)
async def add_holding(req: AddHoldingRequest):
    """Add a new holding or average into an existing one."""
    raw = store.add_holding(
        symbol=req.symbol,
        name=req.name,
        asset_type=req.type.value,
        quantity=req.quantity,
        avg_buy_price=req.avg_buy_price,
    )
    return await _build_holding(raw)


@router.patch("/{symbol}", response_model=PortfolioHolding)
async def update_holding(symbol: str, req: UpdateHoldingRequest):
    """Update quantity or average buy price for a holding."""
    if req.quantity is None and req.avg_buy_price is None:
        raise HTTPException(status_code=400, detail="At least one field must be provided")
    raw = store.update_holding(symbol, quantity=req.quantity, avg_buy_price=req.avg_buy_price)
    if not raw:
        raise HTTPException(status_code=404, detail=f"Holding '{symbol.upper()}' not found")
    return await _build_holding(raw)


@router.delete("/{symbol}", status_code=204)
async def delete_holding(symbol: str):
    """Remove a holding from the portfolio."""
    if not store.delete_holding(symbol):
        raise HTTPException(status_code=404, detail=f"Holding '{symbol.upper()}' not found")


@router.get("/export", response_class=Response)
async def export_csv():
    """Export portfolio holdings as CSV."""
    raw_holdings = store.get_holdings()
    built = list(await asyncio.gather(*[_build_holding(h) for h in raw_holdings]))
    holdings_data = [
        {
            "asset": {"symbol": holding.asset.symbol, "name": holding.asset.name, "type": holding.asset.type.value},
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
async def import_csv(file: UploadFile = File(...)):
    """Import portfolio holdings from CSV."""
    content = (await file.read()).decode("utf-8")
    holdings = parse_portfolio_csv(content)

    imported = []
    for h in holdings:
        try:
            raw = store.add_holding(
                symbol=h["symbol"],
                name=h.get("name", h["symbol"]),
                asset_type=h.get("type", "stock"),
                quantity=h["quantity"],
                avg_buy_price=h["avg_buy_price"],
            )
            imported.append(raw["symbol"])
        except Exception:
            pass

    return {"imported": len(imported), "symbols": imported}


@router.get("/dividends")
async def get_dividends():
    """Get dividend data for all portfolio holdings."""
    raw_holdings = store.get_holdings()
    symbols = [h["symbol"] for h in raw_holdings]
    if not symbols:
        return {"dividends": {}, "total_annual": 0, "symbols_with_dividends": 0}
    return get_portfolio_dividends(symbols)
