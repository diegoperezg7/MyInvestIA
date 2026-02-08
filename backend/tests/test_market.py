"""Tests for market data API endpoints.

Uses mocked market data to avoid real network calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_market_overview(client):
    """Market overview should return top gainers and losers."""
    mock_movers = {
        "gainers": [
            {"symbol": "NVDA", "name": "NVDA", "price": 800.0, "change_percent": 5.0, "volume": 1000000},
        ],
        "losers": [
            {"symbol": "META", "name": "META", "price": 400.0, "change_percent": -3.0, "volume": 500000},
        ],
    }
    with patch("app.routers.market.market_data_service") as mock_svc:
        mock_svc.get_top_movers = MagicMock(return_value=mock_movers)
        response = await client.get("/api/v1/market/")

    assert response.status_code == 200
    data = response.json()
    assert len(data["top_gainers"]) == 1
    assert data["top_gainers"][0]["symbol"] == "NVDA"
    assert len(data["top_losers"]) == 1
    assert data["top_losers"][0]["symbol"] == "META"


@pytest.mark.asyncio
async def test_get_quote_stock(client):
    """Quote endpoint should return asset data."""
    mock_quote = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "price": 195.0,
        "change_percent": 1.2,
        "volume": 55000000,
        "previous_close": 192.7,
        "market_cap": 3000000000000,
    }
    with patch("app.routers.market.market_data_service") as mock_svc:
        mock_svc.get_quote = AsyncMock(return_value=mock_quote)
        response = await client.get("/api/v1/market/quote/AAPL")

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["price"] == 195.0
    assert data["change_percent"] == 1.2


@pytest.mark.asyncio
async def test_get_quote_not_found(client):
    """Quote for invalid symbol should return 404."""
    with patch("app.routers.market.market_data_service") as mock_svc:
        mock_svc.get_quote = AsyncMock(return_value=None)
        response = await client.get("/api/v1/market/quote/INVALID")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_history(client):
    """History endpoint should return OHLCV data."""
    mock_history = [
        {"date": "2025-01-01T00:00:00", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 1000000},
        {"date": "2025-01-02T00:00:00", "open": 103.0, "high": 107.0, "low": 102.0, "close": 106.0, "volume": 1200000},
    ]
    with patch("app.routers.market.market_data_service") as mock_svc:
        mock_svc.get_history = MagicMock(return_value=mock_history)
        response = await client.get("/api/v1/market/history/AAPL?period=1mo&interval=1d")

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["period"] == "1mo"
    assert len(data["data"]) == 2


@pytest.mark.asyncio
async def test_get_history_not_found(client):
    """Empty history should return 404."""
    with patch("app.routers.market.market_data_service") as mock_svc:
        mock_svc.get_history = MagicMock(return_value=[])
        response = await client.get("/api/v1/market/history/INVALID")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_technical_analysis(client):
    """Technical analysis should compute indicators from history."""
    # Generate 60 days of mock price data
    mock_history = [
        {"date": f"2025-01-{i+1:02d}", "open": 100 + i, "high": 102 + i,
         "low": 99 + i, "close": 101.0 + i * 0.5, "volume": 1000000}
        for i in range(60)
    ]
    with patch("app.routers.market.market_data_service") as mock_svc:
        mock_svc.get_history = MagicMock(return_value=mock_history)
        response = await client.get("/api/v1/market/analysis/AAPL")

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["overall_signal"] in ("bullish", "bearish", "neutral")
    assert "rsi" in data
    assert "macd" in data
    assert "sma" in data
    assert "ema" in data
    assert "bollinger_bands" in data
    assert data["signal_counts"]["bullish"] + data["signal_counts"]["bearish"] + data["signal_counts"]["neutral"] == 5


@pytest.mark.asyncio
async def test_get_technical_analysis_insufficient_data(client):
    """Too little data should return 404."""
    mock_history = [
        {"date": f"2025-01-{i+1:02d}", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000}
        for i in range(10)
    ]
    with patch("app.routers.market.market_data_service") as mock_svc:
        mock_svc.get_history = MagicMock(return_value=mock_history)
        response = await client.get("/api/v1/market/analysis/TINY")

    assert response.status_code == 404
