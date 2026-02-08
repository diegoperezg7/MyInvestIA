from fastapi import APIRouter, HTTPException

from app.schemas.asset import (
    AddHoldingRequest,
    Asset,
    Portfolio,
    PortfolioHolding,
    UpdateHoldingRequest,
)
from app.services.store import store

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _build_holding(h: dict) -> PortfolioHolding:
    """Convert a store holding dict into a PortfolioHolding with computed fields."""
    asset = Asset(
        symbol=h["symbol"],
        name=h["name"],
        type=h["type"],
        price=0.0,  # will be populated once market data service is connected
        change_percent=0.0,
        volume=0.0,
    )
    current_value = h["quantity"] * h["avg_buy_price"]  # approximation without live price
    cost_basis = h["quantity"] * h["avg_buy_price"]
    unrealized_pnl = current_value - cost_basis
    unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0.0

    return PortfolioHolding(
        asset=asset,
        quantity=h["quantity"],
        avg_buy_price=h["avg_buy_price"],
        current_value=current_value,
        unrealized_pnl=unrealized_pnl,
        unrealized_pnl_percent=unrealized_pnl_pct,
    )


@router.get("/", response_model=Portfolio)
async def get_portfolio():
    """Get the full portfolio with all holdings."""
    raw_holdings = store.get_holdings()
    holdings = [_build_holding(h) for h in raw_holdings]
    total_value = sum(h.current_value for h in holdings)
    return Portfolio(
        total_value=total_value,
        daily_pnl=0.0,
        daily_pnl_percent=0.0,
        holdings=holdings,
    )


@router.get("/{symbol}", response_model=PortfolioHolding)
async def get_holding(symbol: str):
    """Get a single holding by symbol."""
    raw = store.get_holding(symbol)
    if not raw:
        raise HTTPException(status_code=404, detail=f"Holding '{symbol.upper()}' not found")
    return _build_holding(raw)


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
    return _build_holding(raw)


@router.patch("/{symbol}", response_model=PortfolioHolding)
async def update_holding(symbol: str, req: UpdateHoldingRequest):
    """Update quantity or average buy price for a holding."""
    if req.quantity is None and req.avg_buy_price is None:
        raise HTTPException(status_code=400, detail="At least one field must be provided")
    raw = store.update_holding(symbol, quantity=req.quantity, avg_buy_price=req.avg_buy_price)
    if not raw:
        raise HTTPException(status_code=404, detail=f"Holding '{symbol.upper()}' not found")
    return _build_holding(raw)


@router.delete("/{symbol}", status_code=204)
async def delete_holding(symbol: str):
    """Remove a holding from the portfolio."""
    if not store.delete_holding(symbol):
        raise HTTPException(status_code=404, detail=f"Holding '{symbol.upper()}' not found")
