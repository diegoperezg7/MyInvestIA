"""User profile and personalization endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies import AuthUser, get_current_user
from app.services.profile_service import load_profile, save_profile

router = APIRouter(prefix="/user", tags=["user"])


class UserProfile(BaseModel):
    display_name: str = ""
    risk_tolerance: str = Field(
        default="moderate",
        pattern=r"^(conservative|moderate|aggressive)$",
    )
    investment_horizon: str = Field(
        default="medium",
        pattern=r"^(short|medium|long)$",
    )
    goals: list[str] = []
    preferred_currency: str = "EUR"
    notification_frequency: str = Field(
        default="important",
        pattern=r"^(all|important|critical_only|none)$",
    )
    notification_channels: list[str] = ["telegram"]
    language: str = "es"
    theme: str = "dark"
    assistant_mode: str = Field(
        default="balanced",
        pattern=r"^(prudent|balanced|proactive)$",
    )
    default_horizon: str = Field(
        default="medium",
        pattern=r"^(short|medium|long)$",
    )
    inbox_scope_preference: str = Field(
        default="portfolio",
        pattern=r"^(portfolio|watchlist|macro|research)$",
    )


@router.get("/profile", response_model=UserProfile)
async def get_profile(user: AuthUser = Depends(get_current_user)):
    return UserProfile(**load_profile(user.id, user.tenant_id))


@router.put("/profile", response_model=UserProfile)
async def update_profile(
    profile: UserProfile,
    user: AuthUser = Depends(get_current_user),
):
    saved = save_profile(user.id, profile.model_dump(), user.tenant_id)
    return UserProfile(**saved)


@router.get("/profile/summary")
async def get_profile_summary(user: AuthUser = Depends(get_current_user)):
    data = load_profile(user.id, user.tenant_id)
    return {
        "risk_tolerance": data["risk_tolerance"],
        "investment_horizon": data["investment_horizon"],
        "goals": data["goals"],
        "preferred_currency": data["preferred_currency"],
        "language": data["language"],
        "assistant_mode": data["assistant_mode"],
        "default_horizon": data["default_horizon"],
        "inbox_scope_preference": data["inbox_scope_preference"],
    }
