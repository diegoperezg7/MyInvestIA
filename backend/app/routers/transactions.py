"""Transaction history router for tracking buy/sell/dividend transactions."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.schemas.transactions import CostBasis, Transaction, TransactionCreate

router = APIRouter(prefix="/transactions", tags=["transactions"])

# In-memory store (would use Supabase in production)
_transactions: list[Transaction] = []


@router.get("/")
async def list_transactions(symbol: str | None = None, limit: int = 100):
    """List transactions, optionally filtered by symbol."""
    txns = _transactions
    if symbol:
        txns = [t for t in txns if t.symbol.upper() == symbol.upper()]
    return {"transactions": txns[-limit:], "total": len(txns)}


@router.post("/", response_model=Transaction)
async def create_transaction(req: TransactionCreate):
    """Record a new transaction."""
    txn = Transaction(
        id=str(uuid.uuid4()),
        symbol=req.symbol.upper(),
        type=req.type,
        quantity=req.quantity,
        price=req.price,
        total=round(req.quantity * req.price, 2),
        date=req.date or datetime.now(timezone.utc).isoformat(),
        notes=req.notes,
    )
    _transactions.append(txn)
    return txn


@router.get("/{symbol}/cost-basis", response_model=CostBasis)
async def get_cost_basis(symbol: str):
    """Calculate cost basis for a symbol."""
    symbol = symbol.upper()
    txns = [t for t in _transactions if t.symbol == symbol]

    if not txns:
        raise HTTPException(status_code=404, detail=f"No transactions for {symbol}")

    total_shares = 0.0
    total_invested = 0.0
    realized_pnl = 0.0
    avg_cost = 0.0

    for txn in txns:
        if txn.type.value == "buy":
            total_invested += txn.total
            total_shares += txn.quantity
            avg_cost = total_invested / total_shares if total_shares else 0
        elif txn.type.value == "sell":
            realized_pnl += (txn.price - avg_cost) * txn.quantity
            total_shares -= txn.quantity
            total_invested = avg_cost * total_shares if total_shares > 0 else 0

    return CostBasis(
        symbol=symbol,
        total_shares=round(total_shares, 4),
        average_cost=round(avg_cost, 4),
        total_invested=round(total_invested, 2),
        realized_pnl=round(realized_pnl, 2),
        transactions_count=len(txns),
    )


@router.delete("/{transaction_id}")
async def delete_transaction(transaction_id: str):
    """Delete a transaction."""
    global _transactions
    before = len(_transactions)
    _transactions = [t for t in _transactions if t.id != transaction_id]
    if len(_transactions) == before:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"deleted": True}
