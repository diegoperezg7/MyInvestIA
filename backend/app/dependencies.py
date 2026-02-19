"""Authentication dependencies for FastAPI endpoints.

Validates JWT tokens issued by AIdentity (primary) or Supabase Auth/GoTrue (fallback).
"""

import logging
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AuthUser:
    id: str          # UUID from iam_users or auth.users
    email: str
    role: str        # "admin" or "user"


def get_current_user(request: Request) -> AuthUser:
    """Extract and validate user from Authorization header or darc3_token cookie."""
    token = ""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]

    if not token:
        token = request.cookies.get("darc3_token", "")

    if not token:
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")

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
                    return AuthUser(id=user_id, email=email, role=role)
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
                return AuthUser(id=user_id, email=email, role=role)
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
