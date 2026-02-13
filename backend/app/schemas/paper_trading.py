"""Paper trading schemas."""

from enum import Enum

from pydantic import BaseModel, Field


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class CreateAccountRequest(BaseModel):
    name: str = "Main Paper Account"
    initial_balance: float = Field(default=100000.0, gt=0)


class TradeRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=10)
    side: TradeSide
    quantity: float = Field(gt=0)


class PaperPosition(BaseModel):
    symbol: str
    quantity: float
    avg_price: float
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0


class PaperTrade(BaseModel):
    id: str
    symbol: str
    side: TradeSide
    quantity: float
    price: float
    total: float
    created_at: str


class PaperAccount(BaseModel):
    id: str
    name: str
    balance: float
    initial_balance: float
    total_value: float = 0.0
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0
    positions: list[PaperPosition] = []
    created_at: str = ""
