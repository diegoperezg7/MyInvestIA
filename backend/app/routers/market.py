from fastapi import APIRouter

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/")
async def get_market_overview():
    return {"sentiment_index": 0, "top_gainers": [], "top_losers": [], "macro_indicators": []}
