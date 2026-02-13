"""Paper trading simulation service.

Manages virtual accounts with $100K starting balance,
position tracking, and trade execution at market prices.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.schemas.paper_trading import (
    PaperAccount,
    PaperPosition,
    PaperTrade,
    TradeSide,
)
from app.services.market_data import market_data_service

logger = logging.getLogger(__name__)

# In-memory storage (would use Supabase in production)
_accounts: dict[str, dict] = {}
_trades: dict[str, list[PaperTrade]] = {}
_positions: dict[str, dict[str, dict]] = {}  # account_id -> {symbol -> position}


async def create_account(name: str, initial_balance: float) -> PaperAccount:
    """Create a new paper trading account."""
    account_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    account = {
        "id": account_id,
        "name": name,
        "balance": initial_balance,
        "initial_balance": initial_balance,
        "created_at": now,
    }
    _accounts[account_id] = account
    _trades[account_id] = []
    _positions[account_id] = {}

    # Also store under "default" alias
    _accounts["default"] = account
    _trades["default"] = _trades[account_id]
    _positions["default"] = _positions[account_id]

    return await _build_account_response(account_id)


async def get_account(account_id: str) -> PaperAccount | None:
    """Get account with updated position values."""
    if account_id not in _accounts:
        return None
    return await _build_account_response(account_id)


async def execute_trade(
    account_id: str,
    symbol: str,
    side: TradeSide,
    quantity: float,
) -> PaperTrade:
    """Execute a paper trade at current market price."""
    if account_id not in _accounts:
        raise ValueError("Account not found")

    account = _accounts[account_id]
    symbol = symbol.upper()

    # Get current price
    quote = await market_data_service.get_quote(symbol)
    if not quote:
        raise ValueError(f"Could not get price for {symbol}")

    price = quote["price"]
    total = round(price * quantity, 2)

    if side == TradeSide.BUY:
        if total > account["balance"]:
            raise ValueError(f"Insufficient balance. Need ${total:.2f}, have ${account['balance']:.2f}")
        account["balance"] -= total

        # Update position
        pos = _positions[account_id].get(symbol, {"quantity": 0, "total_cost": 0})
        pos["quantity"] += quantity
        pos["total_cost"] += total
        pos["avg_price"] = pos["total_cost"] / pos["quantity"]
        _positions[account_id][symbol] = pos

    elif side == TradeSide.SELL:
        pos = _positions[account_id].get(symbol)
        if not pos or pos["quantity"] < quantity:
            raise ValueError(f"Insufficient shares of {symbol}")

        account["balance"] += total
        pos["quantity"] -= quantity
        pos["total_cost"] = pos["avg_price"] * pos["quantity"]

        if pos["quantity"] <= 0:
            del _positions[account_id][symbol]
        else:
            _positions[account_id][symbol] = pos

    trade = PaperTrade(
        id=str(uuid.uuid4()),
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        total=total,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _trades[account_id].append(trade)

    return trade


def get_trades(account_id: str) -> list[PaperTrade]:
    """Get trade history for an account."""
    return list(reversed(_trades.get(account_id, [])))


async def _build_account_response(account_id: str) -> PaperAccount:
    """Build account response with current position values (async)."""
    account = _accounts[account_id]
    pos_items = list(_positions.get(account_id, {}).items())

    async def _get_position(symbol: str, pos_data: dict) -> tuple[PaperPosition, float]:
        qty = pos_data["quantity"]
        avg = pos_data["avg_price"]
        current = avg  # fallback
        try:
            quote = await market_data_service.get_quote(symbol)
            if quote:
                current = quote["price"]
        except Exception:
            pass

        market_value = round(current * qty, 2)
        unrealized = round((current - avg) * qty, 2)
        unrealized_pct = round(((current - avg) / avg) * 100, 2) if avg else 0

        position = PaperPosition(
            symbol=symbol,
            quantity=qty,
            avg_price=round(avg, 2),
            current_price=round(current, 2),
            market_value=market_value,
            unrealized_pnl=unrealized,
            unrealized_pnl_percent=unrealized_pct,
        )
        return position, market_value

    results = await asyncio.gather(*[_get_position(sym, data) for sym, data in pos_items])

    positions = [r[0] for r in results]
    total_market_value = sum(r[1] for r in results)

    total_value = round(account["balance"] + total_market_value, 2)
    total_pnl = round(total_value - account["initial_balance"], 2)
    total_pnl_pct = round((total_pnl / account["initial_balance"]) * 100, 2) if account["initial_balance"] else 0

    return PaperAccount(
        id=account["id"],
        name=account["name"],
        balance=round(account["balance"], 2),
        initial_balance=account["initial_balance"],
        total_value=total_value,
        total_pnl=total_pnl,
        total_pnl_percent=total_pnl_pct,
        positions=positions,
        created_at=account.get("created_at", ""),
    )
