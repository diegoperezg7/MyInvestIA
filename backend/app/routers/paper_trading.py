"""Paper trading router."""

from fastapi import APIRouter, HTTPException

from app.schemas.paper_trading import CreateAccountRequest, TradeRequest
from app.services.paper_trading_service import (
    create_account,
    execute_trade,
    get_account,
    get_trades,
)

router = APIRouter(prefix="/paper", tags=["paper-trading"])


@router.post("/accounts")
async def create_paper_account(req: CreateAccountRequest):
    """Create a new paper trading account."""
    return await create_account(req.name, req.initial_balance)


@router.get("/accounts/{account_id}")
async def get_paper_account(account_id: str):
    """Get account details with positions."""
    account = await get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.post("/accounts/{account_id}/trade")
async def paper_trade(account_id: str, req: TradeRequest):
    """Execute a paper trade."""
    try:
        trade = await execute_trade(
            account_id=account_id,
            symbol=req.symbol,
            side=req.side,
            quantity=req.quantity,
        )
        return trade
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/accounts/{account_id}/trades")
async def list_trades(account_id: str):
    """Get trade history for an account."""
    trades = get_trades(account_id)
    return {"trades": trades, "total": len(trades)}


@router.get("/accounts/{account_id}/performance")
async def get_performance(account_id: str):
    """Get performance metrics for an account."""
    account = await get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return {
        "total_value": account.total_value,
        "total_pnl": account.total_pnl,
        "total_pnl_percent": account.total_pnl_percent,
        "cash_balance": account.balance,
        "invested": round(account.total_value - account.balance, 2),
        "positions_count": len(account.positions),
    }
