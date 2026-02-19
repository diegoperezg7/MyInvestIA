"""Authentication endpoints — proxy to Supabase Auth (GoTrue).

Provides login, register (admin-only), refresh, logout, and
a verify endpoint used by Caddy forward_auth for SSO across *.darc3.com.

Password and email changes are handled exclusively by AIdentity.
"""

import logging
import time
from collections import defaultdict
from typing import Optional
from urllib.parse import quote

import httpx
import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, EmailStr

from app.config import settings
from app.dependencies import AuthUser, get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# GoTrue is accessible via the Supabase API gateway (Kong) at /auth/v1
GOTRUE_URL = f"{settings.supabase_url}/auth/v1"

COOKIE_DOMAIN = ".darc3.com"


def _headers(*, use_service_key: bool = False) -> dict:
    """Headers for GoTrue API calls."""
    key = settings.supabase_service_key if use_service_key else settings.supabase_key
    return {
        "apikey": key,
        "Content-Type": "application/json",
    }


# --- Rate limiter ---

_rate_buckets: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(key: str, max_requests: int, window: int):
    """Simple in-memory sliding-window rate limiter."""
    now = time.time()
    bucket = _rate_buckets[key]
    _rate_buckets[key] = [t for t in bucket if now - t < window]
    if len(_rate_buckets[key]) >= max_requests:
        raise HTTPException(
            status_code=429, detail="Too many requests, try again later"
        )
    _rate_buckets[key].append(now)


def _client_ip(request: Request) -> str:
    """Best-effort client IP from X-Forwarded-For or direct connection."""
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# --- Cookie helpers ---


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """Set SSO cookies. Access token is JS-readable (short-lived).
    Refresh token is HttpOnly (long-lived)."""
    response.set_cookie(
        "darc3_token",
        access_token,
        domain=COOKIE_DOMAIN,
        path="/",
        max_age=3600,
        httponly=False,
        secure=True,
        samesite="lax",
    )
    response.set_cookie(
        "darc3_refresh",
        refresh_token,
        domain=COOKIE_DOMAIN,
        path="/",
        max_age=30 * 86400,
        httponly=True,
        secure=True,
        samesite="lax",
    )


def _clear_auth_cookies(response: Response):
    """Delete SSO cookies."""
    response.delete_cookie("darc3_token", domain=COOKIE_DOMAIN, path="/")
    response.delete_cookie("darc3_refresh", domain=COOKIE_DOMAIN, path="/")


# --- Schemas ---


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "user"  # "admin" or "user"


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user: dict


# --- Endpoints ---


@router.get("/verify")
async def verify(request: Request):
    """Validate JWT from cookie or Authorization header.

    Used by Caddy forward_auth to gate access to protected services.
    Returns 200 with user info headers if valid, or 302 redirect to
    the portal login page if invalid/missing.
    """
    token = request.cookies.get("darc3_token")

    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        return _redirect_to_login(request)

    try:
        payload = pyjwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
        return _redirect_to_login(request)

    user_id = payload.get("sub", "")
    email = payload.get("email", "")
    app_meta = payload.get("app_metadata", {})
    user_meta = payload.get("user_metadata", {})
    role = app_meta.get("role") or user_meta.get("role", "user")

    resp = Response(status_code=200)
    resp.headers["X-Auth-User"] = user_id
    resp.headers["X-Auth-Email"] = email
    resp.headers["X-Auth-Role"] = role
    return resp


def _redirect_to_login(request: Request) -> RedirectResponse:
    """Build a redirect to the portal login with ?redirect= preserving the
    original URL the user was trying to access."""
    fwd_scheme = request.headers.get("X-Forwarded-Proto", "https")
    fwd_host = request.headers.get("X-Forwarded-Host", "")
    fwd_uri = request.headers.get("X-Forwarded-Uri", "/")

    original_url = ""
    if fwd_host and fwd_host.endswith(".darc3.com") and fwd_scheme == "https":
        original_url = f"{fwd_scheme}://{fwd_host}{fwd_uri}"

    login_url = "https://portal.darc3.com"
    if original_url:
        login_url += f"?redirect={quote(original_url, safe='')}"

    return RedirectResponse(url=login_url, status_code=302)


@router.post("/login")
async def login(req: LoginRequest, request: Request):
    """Authenticate with email/password. Returns JWT tokens + sets SSO cookies."""
    _check_rate_limit(f"login:{_client_ip(request)}", max_requests=5, window=60)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GOTRUE_URL}/token?grant_type=password",
            headers=_headers(),
            json={"email": req.email, "password": req.password},
        )

    if resp.status_code != 200:
        detail = "Invalid credentials"
        try:
            body = resp.json()
            detail = body.get("error_description") or body.get("msg") or detail
        except Exception:
            pass
        raise HTTPException(status_code=401, detail=detail)

    data = resp.json()
    result = {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_in": data["expires_in"],
        "user": _sanitize_user(data.get("user", {})),
    }

    response = JSONResponse(content=result)
    _set_auth_cookies(response, data["access_token"], data["refresh_token"])
    return response


@router.post("/register")
async def register(req: RegisterRequest, admin: AuthUser = Depends(require_admin)):
    """Create a new user account. Admin-only endpoint.

    The role is stored in app_metadata (not user-writable) so it's included in the JWT.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GOTRUE_URL}/admin/users",
            headers={
                **_headers(use_service_key=True),
                "Authorization": f"Bearer {settings.supabase_service_key}",
            },
            json={
                "email": req.email,
                "password": req.password,
                "email_confirm": True,
                "app_metadata": {"role": req.role},
                "user_metadata": {"role": req.role},
            },
        )

    if resp.status_code not in (200, 201):
        detail = "Registration failed"
        try:
            body = resp.json()
            detail = body.get("msg") or body.get("error_description") or detail
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=detail)

    user_data = resp.json()

    # Auto-login the new user to return tokens
    async with httpx.AsyncClient() as client:
        login_resp = await client.post(
            f"{GOTRUE_URL}/token?grant_type=password",
            headers=_headers(),
            json={"email": req.email, "password": req.password},
        )

    if login_resp.status_code == 200:
        data = login_resp.json()
        result = {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_in": data["expires_in"],
            "user": _sanitize_user(data.get("user", {})),
        }
        response = JSONResponse(content=result)
        _set_auth_cookies(response, data["access_token"], data["refresh_token"])
        return response

    return JSONResponse(
        content={
            "access_token": "",
            "refresh_token": "",
            "expires_in": 0,
            "user": _sanitize_user(user_data),
        }
    )


@router.post("/refresh")
async def refresh_token(request: Request, req: RefreshRequest = None):
    """Refresh an expired access token. Reads refresh_token from body or HttpOnly cookie."""
    _check_rate_limit(f"refresh:{_client_ip(request)}", max_requests=10, window=60)

    # Try body first, then HttpOnly cookie
    token = (req.refresh_token if req else None) or request.cookies.get("darc3_refresh")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GOTRUE_URL}/token?grant_type=refresh_token",
            headers=_headers(),
            json={"refresh_token": token},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    data = resp.json()
    result = {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_in": data["expires_in"],
        "user": _sanitize_user(data.get("user", {})),
    }

    response = JSONResponse(content=result)
    _set_auth_cookies(response, data["access_token"], data["refresh_token"])
    return response


@router.post("/logout")
async def logout(request: Request, user: AuthUser = Depends(get_current_user)):
    """Logout — invalidate the current session on the GoTrue side and clear cookies."""
    auth_header = request.headers.get("Authorization", "")
    user_token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not user_token:
        user_token = request.cookies.get("darc3_token", "")

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{GOTRUE_URL}/logout",
            headers={
                **_headers(),
                "Authorization": f"Bearer {user_token}",
            },
        )

    response = JSONResponse(content={"message": "Logged out"})
    _clear_auth_cookies(response)
    return response


@router.get("/me")
async def get_me(user: AuthUser = Depends(get_current_user)):
    """Get the current authenticated user info."""
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
    }


def _sanitize_user(user: dict) -> dict:
    """Return a safe subset of GoTrue user data."""
    app_meta = user.get("app_metadata", {})
    user_meta = user.get("user_metadata", {})
    role = app_meta.get("role") or user_meta.get("role", "user")
    return {
        "id": user.get("id", ""),
        "email": user.get("email", ""),
        "role": role,
        "created_at": user.get("created_at", ""),
    }
