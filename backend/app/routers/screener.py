"""Screener router with TradingView integration."""

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.schemas.screener import ScreenerRequest
from app.services.screener_service import get_fields, get_presets, run_screener

router = APIRouter(prefix="/screener", tags=["screener"], dependencies=[Depends(get_current_user)])


@router.post("/scan")
async def scan(req: ScreenerRequest):
    """Run screener with filters and optional preset."""
    return await run_screener(
        market=req.market,
        filters=req.filters,
        preset_id=req.preset_id,
        limit=req.limit,
    )


@router.get("/presets")
async def list_presets():
    """List available screening presets."""
    return {"presets": get_presets()}


@router.get("/fields")
async def list_fields():
    """List available filter fields."""
    return {"fields": get_fields()}
