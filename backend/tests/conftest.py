from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.store import store


@pytest.fixture(autouse=True)
def reset_store():
    """Reset in-memory store before each test to ensure isolation."""
    store.holdings.clear()
    store.watchlists.clear()
    yield
    store.holdings.clear()
    store.watchlists.clear()


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
    with patch("app.routers.portfolio.market_data_service") as mock_svc:
        mock_svc.get_quote = AsyncMock(return_value=None)
        yield mock_svc
