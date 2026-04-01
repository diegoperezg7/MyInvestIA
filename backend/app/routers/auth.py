"""Authentication endpoints — shared auth for Supabase + AIdentity.

Provides login, register (admin-only), refresh, logout, and
a verify endpoint used by Caddy forward_auth for SSO.

Password and email changes are handled exclusively by AIdentity.
"""

import logging
import os
import time
from collections import defaultdict
from typing import Literal, Optional
from urllib.parse import quote

import httpx
import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import AliasChoices, BaseModel, EmailStr, Field

from app.config import settings
from app.dependencies import AuthUser, get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# GoTrue is accessible via the Supabase API gateway (Kong) at /auth/v1
GOTRUE_URL = f"{settings.supabase_url}/auth/v1"
AIDENTITY_URL = settings.aidentity_url.rstrip("/")

COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", "localhost")


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
    login: str = Field(min_length=1, validation_alias=AliasChoices("login", "email"))
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


def _normalize_login(login: str) -> str:
    identifier = login.strip()
    if "@" in identifier:
        return identifier.lower()
    return identifier


def _supabase_enabled() -> bool:
    return bool(settings.supabase_url and settings.supabase_key)


def _aidentity_enabled() -> bool:
    return bool(AIDENTITY_URL and settings.aidentity_secret)


def _decode_auth_token(token: str) -> tuple[Literal["aidentity", "supabase"], dict]:
    if settings.aidentity_secret:
        try:
            payload = pyjwt.decode(
                token,
                settings.aidentity_secret,
                algorithms=["HS256"],
            )
            if payload.get("type") == "access":
                return "aidentity", payload
        except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
            pass

    if settings.jwt_secret:
        payload = pyjwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return "supabase", payload

    raise pyjwt.InvalidTokenError("Unsupported token")


def _expires_in_from_token(token: str, fallback: int = 3600) -> int:
    try:
        _, payload = _decode_auth_token(token)
        exp = int(payload.get("exp", 0))
        if exp:
            return max(exp - int(time.time()), 0)
    except Exception:
        pass
    return fallback


def _sanitize_aidentity_user(user: dict, access_token: str = "") -> dict:
    token_payload: dict = {}
    if access_token:
        try:
            provider, payload = _decode_auth_token(access_token)
            if provider == "aidentity":
                token_payload = payload
        except Exception:
            token_payload = {}

    is_admin = bool(user.get("is_admin") or user.get("is_superadmin"))
    role = user.get("role") or ("admin" if is_admin else token_payload.get("role") or "user")
    return {
        "id": user.get("id") or token_payload.get("sub", ""),
        "email": user.get("email") or token_payload.get("email", ""),
        "role": role,
        "created_at": user.get("created_at", ""),
    }


def _build_auth_response(
    *,
    access_token: str,
    refresh_token: str,
    expires_in: int,
    user: dict,
) -> JSONResponse:
    result = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in,
        "user": user,
    }
    response = JSONResponse(content=result)
    _set_auth_cookies(response, access_token, refresh_token)
    return response


def _extract_error_detail(resp: httpx.Response, default: str) -> str:
    try:
        body = resp.json()
    except Exception:
        return default

    for field in ("detail", "error_description", "msg", "message", "error"):
        value = body.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return default


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
        provider, payload = _decode_auth_token(token)
    except pyjwt.ExpiredSignatureError:
        return _redirect_to_login(request)
    except pyjwt.InvalidTokenError:
        return _redirect_to_login(request)

    user_id = payload.get("sub", "")
    email = payload.get("email", "")
    if provider == "aidentity":
        role = payload.get("role", "user")
    else:
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
    portal_domain = os.getenv("PORTAL_URL", "")
    cookie_domain = COOKIE_DOMAIN.lstrip(".")
    if fwd_host and cookie_domain and fwd_host.endswith(cookie_domain) and fwd_scheme == "https":
        original_url = f"{fwd_scheme}://{fwd_host}{fwd_uri}"

    login_url = portal_domain or "/"
    if original_url:
        login_url += f"?redirect={quote(original_url, safe='')}"

    return RedirectResponse(url=login_url, status_code=302)


@router.post("/login")
async def login(req: LoginRequest, request: Request):
    """Authenticate with email/password. Returns JWT tokens + sets SSO cookies."""
    _check_rate_limit(f"login:{_client_ip(request)}", max_requests=5, window=60)
    login_identifier = _normalize_login(req.login)

    async with httpx.AsyncClient() as client:
        supabase_error = "Invalid credentials"

        if _supabase_enabled() and "@" in login_identifier:
            resp = await client.post(
                f"{GOTRUE_URL}/token?grant_type=password",
                headers=_headers(),
                json={"email": login_identifier, "password": req.password},
            )
            if resp.status_code == 200:
                data = resp.json()
                return _build_auth_response(
                    access_token=data["access_token"],
                    refresh_token=data["refresh_token"],
                    expires_in=data["expires_in"],
                    user=_sanitize_user(data.get("user", {})),
                )
            supabase_error = _extract_error_detail(resp, supabase_error)

        if _aidentity_enabled():
            resp = await client.post(
                f"{AIDENTITY_URL}/auth/login",
                json={"login": login_identifier, "password": req.password},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("requires_2fa"):
                    raise HTTPException(
                        status_code=403,
                        detail="Tu cuenta requiere 2FA en AIdentity y MyInvestIA aún no soporta ese paso.",
                    )
                return _build_auth_response(
                    access_token=data["access_token"],
                    refresh_token=data["refresh_token"],
                    expires_in=_expires_in_from_token(
                        data["access_token"],
                        fallback=data.get("expires_in", 3600),
                    ),
                    user=_sanitize_aidentity_user(
                        data.get("user", {}),
                        data["access_token"],
                    ),
                )
            raise HTTPException(
                status_code=401,
                detail=_extract_error_detail(resp, supabase_error),
            )

    raise HTTPException(status_code=401, detail=supabase_error)


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
        if _supabase_enabled():
            resp = await client.post(
                f"{GOTRUE_URL}/token?grant_type=refresh_token",
                headers=_headers(),
                json={"refresh_token": token},
            )
            if resp.status_code == 200:
                data = resp.json()
                return _build_auth_response(
                    access_token=data["access_token"],
                    refresh_token=data["refresh_token"],
                    expires_in=data["expires_in"],
                    user=_sanitize_user(data.get("user", {})),
                )

        if _aidentity_enabled():
            resp = await client.post(
                f"{AIDENTITY_URL}/auth/refresh",
                json={"refresh_token": token},
            )
            if resp.status_code == 200:
                data = resp.json()
                access_token = data["access_token"]
                refresh_token_value = data["refresh_token"]
                return _build_auth_response(
                    access_token=access_token,
                    refresh_token=refresh_token_value,
                    expires_in=_expires_in_from_token(access_token, fallback=3600),
                    user=_sanitize_aidentity_user({}, access_token),
                )

    raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/logout")
async def logout(request: Request, user: AuthUser = Depends(get_current_user)):
    """Logout — invalidate the current session on the GoTrue side and clear cookies."""
    auth_header = request.headers.get("Authorization", "")
    user_token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not user_token:
        user_token = request.cookies.get("darc3_token", "")

    provider: Literal["aidentity", "supabase"] | None = None
    if user_token:
        try:
            provider, _ = _decode_auth_token(user_token)
        except Exception:
            provider = None

    async with httpx.AsyncClient() as client:
        if provider == "aidentity" and _aidentity_enabled():
            await client.post(
                f"{AIDENTITY_URL}/auth/logout",
                headers={"Authorization": f"Bearer {user_token}"},
            )
        elif provider == "supabase" and _supabase_enabled():
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
