from fastapi import APIRouter

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


@router.get("/")
async def get_watchlists():
    return {"watchlists": []}
