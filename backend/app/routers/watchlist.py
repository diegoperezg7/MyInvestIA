import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import AuthUser, get_current_user
from app.schemas.asset import (
    AddWatchlistAssetRequest,
    Asset,
    CreateWatchlistRequest,
    UpdateWatchlistRequest,
    Watchlist,
    WatchlistList,
)
from app.services.market_data import market_data_service
from app.services.store import store

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


async def _enrich_watchlist(raw: dict) -> Watchlist:
    """Enrich a watchlist's assets with live market prices (parallel)."""
    assets = raw.get("assets", [])

    async def _enrich_one(asset: dict) -> Asset:
        quote = await market_data_service.get_quote(asset["symbol"], asset.get("type"))
        if quote:
            return Asset(
                symbol=asset["symbol"],
                name=asset.get("name", asset["symbol"]),
                type=asset.get("type", "stock"),
                price=quote["price"],
                change_percent=quote["change_percent"],
                volume=quote.get("volume", 0),
            )
        return Asset(**asset)

    enriched_assets = await asyncio.gather(*[_enrich_one(a) for a in assets])
    return Watchlist(id=raw["id"], name=raw["name"], assets=list(enriched_assets))


@router.get("/", response_model=WatchlistList)
async def get_watchlists(user: AuthUser = Depends(get_current_user)):
    """Get all watchlists with live prices."""
    raw = store.get_watchlists(user.id, user.tenant_id)
    watchlists = await asyncio.gather(*[_enrich_watchlist(wl) for wl in raw])
    return WatchlistList(watchlists=list(watchlists), total=len(watchlists))


@router.get("/{watchlist_id}", response_model=Watchlist)
async def get_watchlist(watchlist_id: str, user: AuthUser = Depends(get_current_user)):
    """Get a single watchlist by ID with live prices."""
    raw = store.get_watchlist(user.id, watchlist_id, user.tenant_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return await _enrich_watchlist(raw)


@router.post("/", response_model=Watchlist, status_code=201)
async def create_watchlist(
    req: CreateWatchlistRequest, user: AuthUser = Depends(get_current_user)
):
    """Create a new watchlist."""
    raw = store.create_watchlist(
        user_id=user.id, name=req.name, tenant_id=user.tenant_id
    )
    return Watchlist(**raw)


@router.patch("/{watchlist_id}", response_model=Watchlist)
async def update_watchlist(
    watchlist_id: str,
    req: UpdateWatchlistRequest,
    user: AuthUser = Depends(get_current_user),
):
    """Rename a watchlist."""
    raw = store.update_watchlist(
        user.id, watchlist_id, name=req.name, tenant_id=user.tenant_id
    )
    if not raw:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return Watchlist(**raw)


@router.delete("/{watchlist_id}", status_code=204)
async def delete_watchlist(
    watchlist_id: str, user: AuthUser = Depends(get_current_user)
):
    """Delete a watchlist."""
    if not store.delete_watchlist(user.id, watchlist_id, user.tenant_id):
        raise HTTPException(status_code=404, detail="Watchlist not found")


@router.post("/{watchlist_id}/assets", response_model=Watchlist)
async def add_asset_to_watchlist(
    watchlist_id: str,
    req: AddWatchlistAssetRequest,
    user: AuthUser = Depends(get_current_user),
):
    """Add an asset to a watchlist."""
    raw = store.add_asset_to_watchlist(
        user_id=user.id,
        watchlist_id=watchlist_id,
        symbol=req.symbol,
        name=req.name,
        asset_type=req.type.value,
        tenant_id=user.tenant_id,
    )
    if not raw:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return Watchlist(**raw)


@router.delete("/{watchlist_id}/assets/{symbol}", response_model=Watchlist)
async def remove_asset_from_watchlist(
    watchlist_id: str, symbol: str, user: AuthUser = Depends(get_current_user)
):
    """Remove an asset from a watchlist."""
    raw = store.remove_asset_from_watchlist(
        user.id, watchlist_id, symbol, user.tenant_id
    )
    if not raw:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return Watchlist(**raw)
