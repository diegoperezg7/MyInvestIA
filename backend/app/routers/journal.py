"""Journal and decision log API."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import AuthUser, get_current_user
from app.services import journal_service

router = APIRouter(prefix="/journal", tags=["journal"])


@router.get("/")
async def list_journal(
    limit: int = Query(default=50, le=200),
    entry_type: str | None = Query(default=None),
    user: AuthUser = Depends(get_current_user),
):
    entries = journal_service.list_journal_entries(
        user.id,
        user.tenant_id,
        limit=limit,
        entry_type=entry_type,
    )
    return {"entries": entries, "total": len(entries)}


@router.get("/stats")
async def get_journal_stats(user: AuthUser = Depends(get_current_user)):
    return journal_service.get_journal_stats(user.id, user.tenant_id)


@router.get("/{entry_id}")
async def get_journal_entry(
    entry_id: str,
    user: AuthUser = Depends(get_current_user),
):
    entry = journal_service.get_journal_entry(user.id, entry_id, user.tenant_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.post("/")
async def create_journal_entry(
    request: dict,
    user: AuthUser = Depends(get_current_user),
):
    entry = journal_service.create_journal_entry(
        user.id,
        request,
        user.tenant_id,
    )
    return entry


@router.patch("/{entry_id}")
async def update_journal_entry(
    entry_id: str,
    request: dict,
    user: AuthUser = Depends(get_current_user),
):
    entry = journal_service.update_journal_entry(
        user.id,
        entry_id,
        request,
        user.tenant_id,
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.delete("/{entry_id}")
async def delete_journal_entry(
    entry_id: str,
    user: AuthUser = Depends(get_current_user),
):
    success = journal_service.delete_journal_entry(user.id, entry_id, user.tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"deleted": True}


@router.post("/{entry_id}/outcome")
async def record_outcome(
    entry_id: str,
    result: str = Query(...),
    notes: str = Query(default=""),
    user: AuthUser = Depends(get_current_user),
):
    if result not in {"success", "failure", "neutral"}:
        raise HTTPException(status_code=400, detail="Invalid result value")
    entry = await journal_service.record_outcome(
        user.id,
        entry_id,
        result,
        notes,
        user.tenant_id,
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.post("/decision-from-thesis/{thesis_id}")
async def create_decision_from_thesis(
    thesis_id: str,
    decision: str = Query(...),
    reason: str = Query(default=""),
    user: AuthUser = Depends(get_current_user),
):
    if decision not in {"buy", "sell", "hold"}:
        raise HTTPException(status_code=400, detail="Invalid decision value")
    try:
        entry = await journal_service.create_decision_from_thesis(
            user.id,
            thesis_id,
            decision,
            reason,
            user.tenant_id,
        )
        return entry
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
