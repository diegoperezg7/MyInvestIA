"""User profile and personalization endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies import AuthUser, get_current_user
from app.services.store import store

router = APIRouter(prefix="/user", tags=["user"])

# Default profile
_DEFAULT_PROFILE = {
    "display_name": "",
    "risk_tolerance": "moderate",
    "investment_horizon": "medium",
    "goals": [],
    "preferred_currency": "EUR",
    "notification_frequency": "important",
    "notification_channels": ["telegram"],
    "language": "es",
    "theme": "dark",
}


class UserProfile(BaseModel):
    display_name: str = ""
    risk_tolerance: str = Field(default="moderate", pattern=r"^(conservative|moderate|aggressive)$")
    investment_horizon: str = Field(default="medium", pattern=r"^(short|medium|long)$")
    goals: list[str] = []
    preferred_currency: str = "EUR"
    notification_frequency: str = Field(
        default="important",
        pattern=r"^(all|important|critical_only|none)$",
    )
    notification_channels: list[str] = ["telegram"]
    language: str = "es"
    theme: str = "dark"


def _load_profile(user_id: str) -> dict:
    """Load profile from ai_memory store."""
    memories = store.get_memories(user_id, category="user_profile", limit=1)
    if memories:
        return {**_DEFAULT_PROFILE, **memories[0].get("metadata", {})}
    return dict(_DEFAULT_PROFILE)


def _save_profile(user_id: str, profile: dict):
    """Save profile to ai_memory store (replace existing)."""
    memories = store.get_memories(user_id, category="user_profile", limit=10)
    for m in memories:
        store.delete_memory(user_id, m["id"])
    store.save_memory(
        user_id=user_id,
        category="user_profile",
        content="User profile settings",
        metadata=profile,
    )


@router.get("/profile", response_model=UserProfile)
async def get_profile(user: AuthUser = Depends(get_current_user)):
    """Get user profile and preferences."""
    data = _load_profile(user.id)
    return UserProfile(**data)


@router.put("/profile", response_model=UserProfile)
async def update_profile(profile: UserProfile, user: AuthUser = Depends(get_current_user)):
    """Update user profile and preferences."""
    data = profile.model_dump()
    _save_profile(user.id, data)
    return profile


@router.get("/profile/summary")
async def get_profile_summary(user: AuthUser = Depends(get_current_user)):
    """Get a summary suitable for AI context injection."""
    data = _load_profile(user.id)
    return {
        "risk_tolerance": data["risk_tolerance"],
        "investment_horizon": data["investment_horizon"],
        "goals": data["goals"],
        "preferred_currency": data["preferred_currency"],
        "language": data["language"],
    }
