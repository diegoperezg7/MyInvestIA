from fastapi import APIRouter

from app.schemas.asset import AlertList

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/", response_model=AlertList)
async def get_alerts():
    """Get all active alerts."""
    return AlertList()
