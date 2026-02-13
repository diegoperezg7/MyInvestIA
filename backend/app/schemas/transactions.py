"""Transaction schemas for portfolio tracking."""

from enum import Enum

from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"


class TransactionCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=10)
    type: TransactionType
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    date: str = ""  # ISO format, defaults to now
    notes: str = ""


class Transaction(BaseModel):
    id: str
    symbol: str
    type: TransactionType
    quantity: float
    price: float
    total: float
    date: str
    notes: str = ""


class CostBasis(BaseModel):
    symbol: str
    total_shares: float
    average_cost: float
    total_invested: float
    realized_pnl: float
    transactions_count: int
