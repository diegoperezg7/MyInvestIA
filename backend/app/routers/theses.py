from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import AuthUser, get_current_user
from app.schemas.workflow import (
    Thesis,
    ThesisCreateRequest,
    ThesisEvent,
    ThesisListResponse,
    ThesisReviewRequest,
    ThesisReviewResponse,
    ThesisUpdateRequest,
)
from app.services.store import store
from app.services.thesis_service import (
    create_thesis,
    list_theses,
    review_thesis,
    update_thesis,
)

router = APIRouter(prefix="/theses", tags=["theses"])


@router.get("/", response_model=ThesisListResponse)
async def read_theses(
    symbol: str | None = Query(default=None),
    user: AuthUser = Depends(get_current_user),
):
    theses = list_theses(user.id, user.tenant_id, symbol=symbol)
    return ThesisListResponse(theses=[Thesis(**thesis) for thesis in theses], total=len(theses))


@router.post("/", response_model=Thesis)
async def create_thesis_endpoint(
    request: ThesisCreateRequest,
    user: AuthUser = Depends(get_current_user),
):
    thesis, _event = create_thesis(user.id, request.model_dump(), user.tenant_id)
    return Thesis(**thesis)


@router.patch("/{thesis_id}", response_model=Thesis)
async def patch_thesis(
    thesis_id: str,
    request: ThesisUpdateRequest,
    user: AuthUser = Depends(get_current_user),
):
    thesis = update_thesis(user.id, thesis_id, request.model_dump(), user.tenant_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    return Thesis(**thesis)


@router.get("/{thesis_id}/events")
async def read_thesis_events(thesis_id: str, user: AuthUser = Depends(get_current_user)):
    thesis = store.get_thesis(user.id, thesis_id, user.tenant_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    events = store.get_thesis_events(user.id, thesis_id, user.tenant_id)
    return {"events": [ThesisEvent(**event) for event in events], "total": len(events)}


@router.post("/{thesis_id}/review", response_model=ThesisReviewResponse)
async def review_thesis_endpoint(
    thesis_id: str,
    request: ThesisReviewRequest,
    user: AuthUser = Depends(get_current_user),
):
    try:
        result = await review_thesis(
            user.id,
            thesis_id,
            user.tenant_id,
            notes=request.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ThesisReviewResponse(**result)
