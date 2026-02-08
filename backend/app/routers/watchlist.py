from fastapi import APIRouter, HTTPException

from app.schemas.asset import (
    AddWatchlistAssetRequest,
    CreateWatchlistRequest,
    UpdateWatchlistRequest,
    Watchlist,
    WatchlistList,
)
from app.services.store import store

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


@router.get("/", response_model=WatchlistList)
async def get_watchlists():
    """Get all watchlists."""
    raw = store.get_watchlists()
    watchlists = [Watchlist(**wl) for wl in raw]
    return WatchlistList(watchlists=watchlists, total=len(watchlists))


@router.get("/{watchlist_id}", response_model=Watchlist)
async def get_watchlist(watchlist_id: str):
    """Get a single watchlist by ID."""
    raw = store.get_watchlist(watchlist_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return Watchlist(**raw)


@router.post("/", response_model=Watchlist, status_code=201)
async def create_watchlist(req: CreateWatchlistRequest):
    """Create a new watchlist."""
    raw = store.create_watchlist(name=req.name)
    return Watchlist(**raw)


@router.patch("/{watchlist_id}", response_model=Watchlist)
async def update_watchlist(watchlist_id: str, req: UpdateWatchlistRequest):
    """Rename a watchlist."""
    raw = store.update_watchlist(watchlist_id, name=req.name)
    if not raw:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return Watchlist(**raw)


@router.delete("/{watchlist_id}", status_code=204)
async def delete_watchlist(watchlist_id: str):
    """Delete a watchlist."""
    if not store.delete_watchlist(watchlist_id):
        raise HTTPException(status_code=404, detail="Watchlist not found")


@router.post("/{watchlist_id}/assets", response_model=Watchlist)
async def add_asset_to_watchlist(watchlist_id: str, req: AddWatchlistAssetRequest):
    """Add an asset to a watchlist."""
    raw = store.add_asset_to_watchlist(
        watchlist_id=watchlist_id,
        symbol=req.symbol,
        name=req.name,
        asset_type=req.type.value,
    )
    if not raw:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return Watchlist(**raw)


@router.delete("/{watchlist_id}/assets/{symbol}", response_model=Watchlist)
async def remove_asset_from_watchlist(watchlist_id: str, symbol: str):
    """Remove an asset from a watchlist."""
    raw = store.remove_asset_from_watchlist(watchlist_id, symbol)
    if not raw:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return Watchlist(**raw)
