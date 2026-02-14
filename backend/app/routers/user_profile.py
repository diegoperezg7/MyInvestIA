"""User profile and personalization endpoints.

Stores user financial profile, risk tolerance, investment horizon,
goals, and communication preferences. Single-user app — no auth needed.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.store import store

router = APIRouter(prefix="/user", tags=["user"])

# Default profile stored in memory
_DEFAULT_PROFILE = {
    "display_name": "",
    "risk_tolerance": "moderate",  # conservative, moderate, aggressive
    "investment_horizon": "medium",  # short (< 1y), medium (1-5y), long (5y+)
    "goals": [],
    "preferred_currency": "EUR",
    "notification_frequency": "important",  # all, important, critical_only, none
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


def _load_profile() -> dict:
    """Load profile from ai_memory store."""
    memories = store.get_memories(category="user_profile", limit=1)
    if memories:
        return {**_DEFAULT_PROFILE, **memories[0].get("metadata", {})}
    return dict(_DEFAULT_PROFILE)


def _save_profile(profile: dict):
    """Save profile to ai_memory store (replace existing)."""
    # Delete old profile entries
    memories = store.get_memories(category="user_profile", limit=10)
    for m in memories:
        store.delete_memory(m["id"])
    # Save new
    store.save_memory(
        category="user_profile",
        content="User profile settings",
        metadata=profile,
    )


@router.get("/profile", response_model=UserProfile)
async def get_profile():
    """Get user profile and preferences."""
    data = _load_profile()
    return UserProfile(**data)


@router.put("/profile", response_model=UserProfile)
async def update_profile(profile: UserProfile):
    """Update user profile and preferences."""
    data = profile.model_dump()
    _save_profile(data)
    return profile


@router.get("/profile/summary")
async def get_profile_summary():
    """Get a summary suitable for AI context injection."""
    data = _load_profile()
    return {
        "risk_tolerance": data["risk_tolerance"],
        "investment_horizon": data["investment_horizon"],
        "goals": data["goals"],
        "preferred_currency": data["preferred_currency"],
        "language": data["language"],
    }
