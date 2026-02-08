from fastapi import APIRouter

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/")
async def get_portfolio():
    return {"holdings": [], "total_value": 0, "daily_pnl": 0, "daily_pnl_percent": 0}
