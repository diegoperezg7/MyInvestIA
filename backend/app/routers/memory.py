"""AI memory endpoints for storing and retrieving context for personalized insights."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.dependencies import AuthUser, get_current_user
from app.services.store import store

router = APIRouter(prefix="/memory", tags=["memory"])


class SaveMemoryRequest(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1, max_length=4000)
    metadata: dict = {}


class MemoryEntry(BaseModel):
    id: str
    category: str
    content: str
    metadata: dict = {}


class MemoryList(BaseModel):
    memories: list[MemoryEntry] = []
    total: int = 0


@router.get("/", response_model=MemoryList)
async def get_memories(
    category: str | None = Query(default=None, description="Filter by category"),
    limit: int = Query(default=50, ge=1, le=200),
    user: AuthUser = Depends(get_current_user),
):
    """Get AI memory entries, optionally filtered by category.

    Categories: alert_history, user_preference, interaction, market_note
    """
    memories = store.get_memories(user.id, category=category, limit=limit)
    entries = [MemoryEntry(**m) for m in memories]
    return MemoryList(memories=entries, total=len(entries))


@router.post("/", response_model=MemoryEntry, status_code=201)
async def save_memory(request: SaveMemoryRequest, user: AuthUser = Depends(get_current_user)):
    """Save an AI memory entry for personalized context."""
    entry = store.save_memory(
        user_id=user.id,
        category=request.category,
        content=request.content,
        metadata=request.metadata,
    )
    return MemoryEntry(**entry)


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str, user: AuthUser = Depends(get_current_user)):
    """Delete an AI memory entry."""
    deleted = store.delete_memory(user.id, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory entry not found")
    return {"deleted": True}
