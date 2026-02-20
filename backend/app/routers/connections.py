"""API router for external connections (exchanges, wallets, brokers, prediction markets)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import AuthUser, get_current_user
from app.schemas.connections import (
    ConnectionDetail,
    ConnectionList,
    ConnectionSummary,
    CreateBrokerConnectionRequest,
    CreateExchangeConnectionRequest,
    CreatePredictionConnectionRequest,
    CreateWalletConnectionRequest,
    SupportedProvider,
    SyncResult,
    TestConnectionResult,
)
from app.services import connection_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connections", tags=["connections"])


@router.get("/providers", response_model=list[SupportedProvider])
async def get_providers(user: AuthUser = Depends(get_current_user)):
    """List all supported connection providers with required fields."""
    return connection_service.get_providers()


@router.get("/", response_model=ConnectionList)
async def list_connections(user: AuthUser = Depends(get_current_user)):
    """List all configured connections with summary info."""
    connections = connection_service.list_connections(user.id)
    return ConnectionList(connections=connections, total=len(connections))


@router.get("/{connection_id}", response_model=ConnectionDetail)
async def get_connection(connection_id: str, user: AuthUser = Depends(get_current_user)):
    """Get connection detail including holdings."""
    conn = connection_service.get_connection(user.id, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return conn


@router.post("/exchange", response_model=ConnectionSummary, status_code=201)
async def create_exchange_connection(req: CreateExchangeConnectionRequest, user: AuthUser = Depends(get_current_user)):
    """Create a new exchange connection (e.g. Binance, Coinbase)."""
    try:
        conn = connection_service.create_exchange_connection(
            user_id=user.id,
            provider=req.provider,
            label=req.label,
            api_key=req.api_key,
            api_secret=req.api_secret,
            passphrase=req.passphrase,
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/wallet", response_model=ConnectionSummary, status_code=201)
async def create_wallet_connection(req: CreateWalletConnectionRequest, user: AuthUser = Depends(get_current_user)):
    """Create a new wallet connection (e.g. MetaMask, Trust Wallet, Ledger)."""
    try:
        conn = await connection_service.create_wallet_connection(
            user_id=user.id,
            label=req.label,
            address=req.address,
            chain=req.chain,
            provider=req.provider,
        )
        return conn
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/broker", response_model=ConnectionSummary, status_code=201)
async def create_broker_connection(req: CreateBrokerConnectionRequest, user: AuthUser = Depends(get_current_user)):
    """Create a new broker connection (eToro, IBKR, Robinhood, etc.)."""
    try:
        conn = connection_service.create_broker_connection(
            user_id=user.id,
            label=req.label,
            api_key=req.api_key,
            api_secret=req.api_secret,
            provider=req.provider,
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/prediction", response_model=ConnectionSummary, status_code=201)
async def create_prediction_connection(req: CreatePredictionConnectionRequest, user: AuthUser = Depends(get_current_user)):
    """Create a new prediction market connection (Polymarket, Kalshi)."""
    try:
        conn = connection_service.create_prediction_connection(
            user_id=user.id,
            label=req.label,
            provider=req.provider,
            api_key=req.api_key,
            wallet_address=req.wallet_address,
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/polymarket", response_model=ConnectionSummary, status_code=201, include_in_schema=False)
async def create_polymarket_connection(req: CreatePredictionConnectionRequest, user: AuthUser = Depends(get_current_user)):
    """Backwards-compatible endpoint."""
    req.provider = "polymarket"
    try:
        conn = connection_service.create_prediction_connection(
            user_id=user.id,
            label=req.label,
            provider=req.provider,
            api_key=req.api_key,
            wallet_address=req.wallet_address,
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{connection_id}", status_code=204)
async def delete_connection(connection_id: str, user: AuthUser = Depends(get_current_user)):
    """Delete a connection and all its synced holdings."""
    if not connection_service.delete_connection(user.id, connection_id):
        raise HTTPException(status_code=404, detail="Connection not found")


@router.post("/{connection_id}/sync", response_model=SyncResult)
async def sync_connection(connection_id: str, user: AuthUser = Depends(get_current_user)):
    """Trigger manual sync for a specific connection."""
    try:
        return await connection_service.sync_connection(user.id, connection_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sync-all", response_model=list[SyncResult])
async def sync_all(user: AuthUser = Depends(get_current_user)):
    """Sync all active connections."""
    return await connection_service.sync_all(user.id)


@router.post("/{connection_id}/test", response_model=TestConnectionResult)
async def test_connection(connection_id: str, user: AuthUser = Depends(get_current_user)):
    """Test connectivity for an existing connection."""
    try:
        return await connection_service.test_connection_by_id(user.id, connection_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{connection_id}/history")
async def get_sync_history(connection_id: str, limit: int = Query(default=20, le=100), user: AuthUser = Depends(get_current_user)):
    """Get synchronization history for a connection."""
    conn = connection_service.get_connection(user.id, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return connection_service.get_sync_history(user.id, connection_id, limit)
