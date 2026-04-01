from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import AuthUser, get_current_user
from app.schemas.workflow import (
    InboxActionRequest,
    InboxItem,
    InboxRefreshResponse,
    InboxResponse,
    Thesis,
    ThesisEvent,
)
from app.services.inbox_service import get_inbox, refresh_inbox, update_inbox_item_state
from app.services.store import store
from app.services.thesis_service import create_thesis_from_inbox_item

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("/", response_model=InboxResponse)
async def read_inbox(
    scope: str | None = Query(default=None),
    status: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
    refresh: bool = Query(default=False),
    user: AuthUser = Depends(get_current_user),
):
    payload = await get_inbox(
        user.id,
        user.tenant_id,
        scope=scope,
        status=status,
        kind=kind,
        symbol=symbol,
        force_refresh=refresh,
    )
    return InboxResponse(**payload)


@router.post("/refresh", response_model=InboxRefreshResponse)
async def rebuild_inbox(user: AuthUser = Depends(get_current_user)):
    payload = await refresh_inbox(user.id, user.tenant_id)
    return InboxRefreshResponse(
        items=[InboxItem(**item) for item in payload["items"]],
        total=len(payload["items"]),
        generated_at=payload["generated_at"],
        cached_until=payload["cached_until"],
        refreshed=True,
    )


@router.patch("/{item_id}", response_model=InboxItem)
async def patch_inbox_item(
    item_id: str,
    request: InboxActionRequest,
    user: AuthUser = Depends(get_current_user),
):
    item = update_inbox_item_state(
        user.id,
        item_id,
        request.action,
        user.tenant_id,
        thesis_id=request.thesis_id,
    )
    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    return InboxItem(**item)


@router.post("/{item_id}/thesis")
async def create_thesis_from_inbox(
    item_id: str, user: AuthUser = Depends(get_current_user)
):
    item = store.get_inbox_item(user.id, item_id, user.tenant_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    thesis, event = await create_thesis_from_inbox_item(user.id, item, user.tenant_id)
    return {"thesis": Thesis(**thesis), "event": ThesisEvent(**event)}
