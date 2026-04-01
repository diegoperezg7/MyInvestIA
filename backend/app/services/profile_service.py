"""Helpers for loading and saving user personalization settings."""

from __future__ import annotations

from app.services.store import store

DEFAULT_PROFILE = {
    "display_name": "",
    "risk_tolerance": "moderate",
    "investment_horizon": "medium",
    "goals": [],
    "preferred_currency": "EUR",
    "notification_frequency": "important",
    "notification_channels": ["telegram"],
    "language": "es",
    "theme": "dark",
    "assistant_mode": "balanced",
    "default_horizon": "medium",
    "inbox_scope_preference": "portfolio",
}


def load_profile(user_id: str, tenant_id: str | None = None) -> dict:
    """Load profile from AI memory and merge with defaults."""
    memories = store.get_memories(
        user_id,
        category="user_profile",
        limit=1,
        tenant_id=tenant_id,
    )
    if memories:
        return {**DEFAULT_PROFILE, **memories[0].get("metadata", {})}
    return dict(DEFAULT_PROFILE)


def save_profile(user_id: str, profile: dict, tenant_id: str | None = None) -> dict:
    """Replace the stored profile."""
    memories = store.get_memories(
        user_id,
        category="user_profile",
        limit=10,
        tenant_id=tenant_id,
    )
    for memory in memories:
        store.delete_memory(user_id, memory["id"], tenant_id)
    store.save_memory(
        user_id=user_id,
        category="user_profile",
        content="User profile settings",
        metadata={**DEFAULT_PROFILE, **profile},
        tenant_id=tenant_id,
    )
    return {**DEFAULT_PROFILE, **profile}
