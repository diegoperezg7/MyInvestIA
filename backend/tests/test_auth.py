from unittest.mock import MagicMock, patch

import jwt
import pytest

from app.config import settings


def _make_response(status_code: int, payload: dict, text: str = ""):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = text
    return response


class _QueuedAsyncClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if not self._responses:
            raise AssertionError(f"Unexpected POST call to {url}")
        return self._responses.pop(0)


def _make_aidentity_access_token(**overrides) -> str:
    payload = {
        "sub": "aidentity-user-1",
        "email": "user@example.com",
        "role": "user",
        "type": "access",
        "exp": 2_000_000_000,
    }
    payload.update(overrides)
    return jwt.encode(payload, settings.aidentity_secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_login_accepts_legacy_login_field(client):
    mock_response = _make_response(
        200,
        {
            "access_token": "header.payload.signature",
            "refresh_token": "refresh-token",
            "expires_in": 3600,
            "user": {
                "id": "user-1",
                "email": "user@example.com",
                "app_metadata": {"role": "user"},
                "user_metadata": {},
                "created_at": "2026-03-06T00:00:00Z",
            },
        },
    )
    mock_client = _QueuedAsyncClient([mock_response])

    with patch("app.routers.auth.httpx.AsyncClient", return_value=mock_client), patch(
        "app.routers.auth._aidentity_enabled",
        return_value=False,
    ):
        response = await client.post(
            "/api/v1/auth/login",
            json={"login": "user@example.com", "password": "secret"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["email"] == "user@example.com"
    assert payload["access_token"] == "header.payload.signature"
    assert mock_client.calls[0][1]["json"]["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_login_falls_back_to_aidentity_when_supabase_rejects_email(client):
    access_token = _make_aidentity_access_token()
    mock_client = _QueuedAsyncClient(
        [
            _make_response(
                400,
                {"error_description": "Invalid login credentials"},
            ),
            _make_response(
                200,
                {
                    "access_token": access_token,
                    "refresh_token": "aidentity-refresh",
                    "user": {
                        "id": "aidentity-user-1",
                        "email": "user@example.com",
                        "is_admin": False,
                        "created_at": "2026-03-06T00:00:00Z",
                    },
                },
            ),
        ]
    )

    with patch("app.routers.auth.httpx.AsyncClient", return_value=mock_client):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "secret"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"] == access_token
    assert payload["refresh_token"] == "aidentity-refresh"
    assert payload["user"]["email"] == "user@example.com"
    assert mock_client.calls[0][0].endswith("/token?grant_type=password")
    assert mock_client.calls[1][0].endswith("/auth/login")


@pytest.mark.asyncio
async def test_login_accepts_username_via_aidentity(client):
    access_token = _make_aidentity_access_token(email="darce@example.com")
    mock_client = _QueuedAsyncClient(
        [
            _make_response(
                200,
                {
                    "access_token": access_token,
                    "refresh_token": "refresh-token",
                    "user": {
                        "id": "aidentity-user-1",
                        "email": "darce@example.com",
                        "is_admin": True,
                    },
                },
            )
        ]
    )

    with patch("app.routers.auth.httpx.AsyncClient", return_value=mock_client):
        response = await client.post(
            "/api/v1/auth/login",
            json={"login": "darce", "password": "secret"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["role"] == "admin"
    assert len(mock_client.calls) == 1
    assert mock_client.calls[0][1]["json"] == {"login": "darce", "password": "secret"}
    assert mock_client.calls[0][0].endswith("/auth/login")


@pytest.mark.asyncio
async def test_login_returns_readable_invalid_credentials(client):
    mock_client = _QueuedAsyncClient(
        [
            _make_response(
                400,
                {"error_description": "Invalid login credentials"},
            ),
            _make_response(
                401,
                {"detail": "Invalid credentials"},
            ),
        ]
    )

    with patch("app.routers.auth.httpx.AsyncClient", return_value=mock_client):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "bad-password"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_refresh_falls_back_to_aidentity(client):
    access_token = _make_aidentity_access_token()
    mock_client = _QueuedAsyncClient(
        [
            _make_response(401, {"error_description": "Invalid refresh token"}),
            _make_response(
                200,
                {
                    "access_token": access_token,
                    "refresh_token": "new-refresh-token",
                },
            ),
        ]
    )

    with patch("app.routers.auth.httpx.AsyncClient", return_value=mock_client):
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "refresh-token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"] == access_token
    assert payload["refresh_token"] == "new-refresh-token"
    assert payload["user"]["email"] == "user@example.com"
    assert mock_client.calls[1][0].endswith("/auth/refresh")


@pytest.mark.asyncio
async def test_verify_accepts_aidentity_token(client):
    access_token = _make_aidentity_access_token(role="admin")
    client.cookies.set("darc3_token", access_token)
    response = await client.get("/api/v1/auth/verify")

    assert response.status_code == 200
    assert response.headers["x-auth-email"] == "user@example.com"
    assert response.headers["x-auth-role"] == "admin"
