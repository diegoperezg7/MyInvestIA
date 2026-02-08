from fastapi import APIRouter

from app.schemas.asset import MarketOverview

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/", response_model=MarketOverview)
async def get_market_overview():
    """Get market overview with sentiment, top movers, and macro indicators."""
    return MarketOverview()
