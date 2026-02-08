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
