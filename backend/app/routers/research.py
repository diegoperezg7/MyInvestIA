from fastapi import APIRouter, Depends, Query

from app.dependencies import AuthUser, get_current_user
from app.schemas.workflow import (
    ResearchFactorResponse,
    ResearchRankingsResponse,
    ResearchScreen,
    ResearchScreenRequest,
    ResearchSnapshotListResponse,
)
from app.services.research_service import (
    get_rankings,
    get_symbol_factors,
    list_snapshots,
    save_screen,
)
from app.services.store import store

router = APIRouter(prefix="/research", tags=["research"])


@router.get("/rankings", response_model=ResearchRankingsResponse)
async def read_rankings(
    symbols: str | None = Query(default=None, description="Comma-separated extra symbols"),
    save_snapshot: bool = Query(default=False),
    user: AuthUser = Depends(get_current_user),
):
    extra_symbols = [value.strip().upper() for value in (symbols or "").split(",") if value.strip()]
    payload = await get_rankings(
        user.id,
        user.tenant_id,
        extra_symbols=extra_symbols,
        save_snapshot=save_snapshot,
    )
    return ResearchRankingsResponse(**payload)


@router.get("/factors/{symbol}", response_model=ResearchFactorResponse)
async def read_symbol_factors(symbol: str):
    return ResearchFactorResponse(**(await get_symbol_factors(symbol)))


@router.get("/screens")
async def read_saved_screens(user: AuthUser = Depends(get_current_user)):
    screens = store.get_research_screens(user.id, user.tenant_id)
    return {"screens": [ResearchScreen(**screen) for screen in screens], "total": len(screens)}


@router.post("/screens", response_model=ResearchScreen)
async def create_screen(
    request: ResearchScreenRequest,
    user: AuthUser = Depends(get_current_user),
):
    return ResearchScreen(**save_screen(user.id, request.model_dump(), user.tenant_id))


@router.get("/snapshots", response_model=ResearchSnapshotListResponse)
async def read_snapshots(user: AuthUser = Depends(get_current_user)):
    return ResearchSnapshotListResponse(**list_snapshots(user.id, user.tenant_id))
