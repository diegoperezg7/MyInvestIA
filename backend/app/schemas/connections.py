"""Schemas for external connections (exchanges, wallets, brokers, prediction markets)."""

from enum import Enum

from pydantic import BaseModel, Field


class ConnectionType(str, Enum):
    EXCHANGE = "exchange"
    WALLET = "wallet"
    BROKER = "broker"
    PREDICTION = "prediction"


class ConnectionStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class SyncStatus(str, Enum):
    NEVER = "never"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


# --- Request Schemas ---


class CreateExchangeConnectionRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=50, description="Exchange provider (e.g. binance)")
    label: str = Field(min_length=1, max_length=100)
    api_key: str = Field(min_length=1)
    api_secret: str = Field(min_length=1)
    passphrase: str | None = None


class CreateWalletConnectionRequest(BaseModel):
    provider: str = Field(default="metamask", max_length=50, description="Wallet provider (e.g. metamask, trustwallet, ledger)")
    label: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=256)
    chain: str = Field(default="ethereum", max_length=50)


class CreateBrokerConnectionRequest(BaseModel):
    provider: str = Field(default="etoro", max_length=50, description="Broker provider (e.g. etoro, ibkr, robinhood)")
    label: str = Field(min_length=1, max_length=100)
    api_key: str = Field(min_length=1)
    api_secret: str = Field(min_length=1)


class CreatePredictionConnectionRequest(BaseModel):
    provider: str = Field(default="polymarket", max_length=50, description="Prediction market provider (e.g. polymarket, kalshi)")
    label: str = Field(min_length=1, max_length=100)
    api_key: str | None = None
    wallet_address: str | None = None


# --- Response Schemas ---


class ConnectionSummary(BaseModel):
    id: str
    type: ConnectionType
    provider: str
    label: str
    status: ConnectionStatus
    last_sync_at: str | None = None
    last_sync_status: str | None = None
    last_sync_error: str | None = None
    sync_count: int = 0
    holdings_count: int = 0
    total_value: float = 0.0
    created_at: str | None = None


class ConnectionDetail(ConnectionSummary):
    metadata: dict = {}
    wallet_address: str | None = None
    chain: str | None = None
    holdings: list[dict] = []


class ConnectionList(BaseModel):
    connections: list[ConnectionSummary] = []
    total: int = 0


class SyncResult(BaseModel):
    connection_id: str
    status: str
    holdings_synced: int = 0
    holdings_added: int = 0
    holdings_updated: int = 0
    holdings_removed: int = 0
    duration_ms: int = 0
    error: str | None = None


class TestConnectionResult(BaseModel):
    success: bool
    message: str
    account_info: dict = {}


class SupportedProvider(BaseModel):
    id: str
    name: str
    type: ConnectionType
    description: str
    fields_required: list[str]
    logo_url: str | None = None
