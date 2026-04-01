from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import AuthUser, get_current_user

# Force InMemoryStore for all tests (regardless of Supabase .env config)
import app.services.store as store_module
from app.services.store import InMemoryStore

_test_store = InMemoryStore()
store_module.store = _test_store

from app.main import app  # noqa: E402 — import after store override


def _fake_user() -> AuthUser:
    return AuthUser(
        id="test-user",
        email="test@example.com",
        role="admin",
        tenant_id="default",
    )


app.dependency_overrides[get_current_user] = _fake_user


@pytest.fixture(autouse=True)
def reset_store():
    """Reset in-memory store before each test to ensure isolation."""
    _test_store._tenants.clear()
    yield
    _test_store._tenants.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_market_data():
    """Mock market data service to avoid real API calls in tests.

    Returns the mock so tests can customize return values.
    The mock returns None by default (triggers fallback to avg_buy_price).
    """
    with patch("app.routers.portfolio.market_data_service") as mock_svc, \
         patch("app.routers.portfolio.convert_currency") as mock_fx:
        mock_svc.get_quote = AsyncMock(return_value=None)
        mock_fx.return_value = {"rate": 1.0}
        yield mock_svc
