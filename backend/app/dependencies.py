"""Authentication dependencies for FastAPI endpoints.

Validates JWT tokens issued by AIdentity (primary) or Supabase Auth/GoTrue (fallback).
Supports multi-tenancy via X-Tenant-ID header.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import jwt
import httpx
from fastapi import Depends, HTTPException, Request, Header

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AuthUser:
    id: str  # UUID from iam_users or auth.users
    email: str
    role: str  # "admin" or "user"
    tenant_id: Optional[str] = None  # Multi-tenant: tenant identifier


def _resolve_supabase_user_by_email(email: str) -> str | None:
    """Look up the Supabase auth user UUID by email using the admin API."""
    if not settings.supabase_url or not (
        settings.supabase_service_key or settings.supabase_key
    ):
        return None
    try:
        service_key = settings.supabase_service_key or settings.supabase_key
        url = f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users"
        resp = httpx.get(
            url,
            headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
            params={"email": email},
            timeout=5,
        )
        if resp.status_code == 200:
            users = resp.json().get("users", [])
            if users:
                return users[0].get("id")
    except Exception as e:
        logger.warning("Could not resolve Supabase user by email %s: %s", email, e)
    return None


def _create_supabase_user_if_not_exists(email: str) -> str | None:
    """Create a Supabase user if they don't exist. Returns the user ID or None on failure."""
    try:
        service_key = settings.supabase_service_key or settings.supabase_key
        url = f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users"

        import secrets

        temp_password = secrets.token_urlsafe(16)

        resp = httpx.post(
            url,
            headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
            json={
                "email": email,
                "password": temp_password,
                "email_confirm": True,
                "user_metadata": {"source": "aidentity"},
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            user_data = resp.json()
            user_id = user_data.get("id")
            logger.info("Created Supabase user for AIdentity user: %s", email)
            return user_id
        elif resp.status_code == 400:
            return _resolve_supabase_user_by_email(email)
        else:
            logger.warning("Failed to create Supabase user: %s", resp.text)
    except Exception as e:
        logger.error("Error creating Supabase user: %s", e)
    return None


def get_current_user(
    request: Request, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> AuthUser:
    """Extract and validate user from Authorization header or darc3_token cookie.

    Supports multi-tenancy via X-Tenant-ID header.
    """
    token = ""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]

    if not token:
        token = request.cookies.get("darc3_token", "")

    if not token:
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")

    tenant_id = (
        x_tenant_id or settings.default_tenant_id
        if settings.enable_multitenant
        else settings.default_tenant_id
    )

    # Try AIdentity JWT first (no audience required)
    if settings.aidentity_secret:
        try:
            payload = jwt.decode(
                token,
                settings.aidentity_secret,
                algorithms=["HS256"],
            )
            # AIdentity format: role is at top level, type must be "access"
            if payload.get("type") == "access":
                user_id = payload.get("sub")
                email = payload.get("email", "")
                role = payload.get("role", "user")
                if user_id:
                    # Resolve Supabase user_id if Supabase is configured
                    supabase_user_id = _resolve_supabase_user_by_email(email)
                    if not supabase_user_id:
                        # Auto-create user in Supabase if not exists
                        logger.info(
                            "AIdentity user %s not found in Supabase, creating...",
                            email,
                        )
                        supabase_user_id = _create_supabase_user_if_not_exists(email)
                    if supabase_user_id:
                        return AuthUser(
                            id=supabase_user_id,
                            email=email,
                            role=role,
                            tenant_id=tenant_id,
                        )
                    # If no Supabase user found, use AIdentity user_id
                    # (for apps using InMemoryStore)
                    return AuthUser(
                        id=user_id, email=email, role=role, tenant_id=tenant_id
                    )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            pass  # Fall through to GoTrue validation

    # Fallback: GoTrue/Supabase JWT
    if settings.jwt_secret:
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
            user_id = payload.get("sub")
            email = payload.get("email", "")
            app_metadata = payload.get("app_metadata", {})
            user_metadata = payload.get("user_metadata", {})
            role = app_metadata.get("role") or user_metadata.get("role", "user")
            if user_id:
                return AuthUser(id=user_id, email=email, role=role, tenant_id=tenant_id)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid JWT: %s", e)

    raise HTTPException(status_code=401, detail="Invalid token")


def require_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Require the authenticated user to have admin role."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
