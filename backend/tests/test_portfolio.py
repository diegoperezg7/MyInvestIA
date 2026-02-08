import pytest


@pytest.mark.asyncio
async def test_get_empty_portfolio(client, mock_market_data):
    response = await client.get("/api/v1/portfolio/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_value"] == 0.0
    assert data["holdings"] == []


@pytest.mark.asyncio
async def test_add_holding(client, mock_market_data):
    payload = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "type": "stock",
        "quantity": 10,
        "avg_buy_price": 150.0,
    }
    response = await client.post("/api/v1/portfolio/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["asset"]["symbol"] == "AAPL"
    assert data["asset"]["name"] == "Apple Inc."
    assert data["quantity"] == 10
    assert data["avg_buy_price"] == 150.0
    assert data["current_value"] == 1500.0


@pytest.mark.asyncio
async def test_add_holding_averages_existing(client, mock_market_data):
    payload = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "type": "stock",
        "quantity": 10,
        "avg_buy_price": 100.0,
    }
    await client.post("/api/v1/portfolio/", json=payload)

    # Add more shares at a different price
    payload2 = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "type": "stock",
        "quantity": 10,
        "avg_buy_price": 200.0,
    }
    response = await client.post("/api/v1/portfolio/", json=payload2)
    assert response.status_code == 201
    data = response.json()
    assert data["quantity"] == 20
    assert data["avg_buy_price"] == 150.0  # weighted average


@pytest.mark.asyncio
async def test_get_holding_by_symbol(client, mock_market_data):
    payload = {
        "symbol": "TSLA",
        "name": "Tesla Inc.",
        "type": "stock",
        "quantity": 5,
        "avg_buy_price": 250.0,
    }
    await client.post("/api/v1/portfolio/", json=payload)

    response = await client.get("/api/v1/portfolio/TSLA")
    assert response.status_code == 200
    data = response.json()
    assert data["asset"]["symbol"] == "TSLA"
    assert data["quantity"] == 5


@pytest.mark.asyncio
async def test_get_holding_not_found(client, mock_market_data):
    response = await client.get("/api/v1/portfolio/NONEXIST")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_holding_quantity(client, mock_market_data):
    payload = {
        "symbol": "BTC",
        "name": "Bitcoin",
        "type": "crypto",
        "quantity": 1.0,
        "avg_buy_price": 40000.0,
    }
    await client.post("/api/v1/portfolio/", json=payload)

    response = await client.patch("/api/v1/portfolio/BTC", json={"quantity": 2.0})
    assert response.status_code == 200
    data = response.json()
    assert data["quantity"] == 2.0
    assert data["avg_buy_price"] == 40000.0  # unchanged


@pytest.mark.asyncio
async def test_update_holding_avg_price(client, mock_market_data):
    payload = {
        "symbol": "ETH",
        "name": "Ethereum",
        "type": "crypto",
        "quantity": 5.0,
        "avg_buy_price": 3000.0,
    }
    await client.post("/api/v1/portfolio/", json=payload)

    response = await client.patch("/api/v1/portfolio/ETH", json={"avg_buy_price": 3500.0})
    assert response.status_code == 200
    data = response.json()
    assert data["avg_buy_price"] == 3500.0


@pytest.mark.asyncio
async def test_update_holding_no_fields(client, mock_market_data):
    payload = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "type": "stock",
        "quantity": 10,
        "avg_buy_price": 150.0,
    }
    await client.post("/api/v1/portfolio/", json=payload)

    response = await client.patch("/api/v1/portfolio/AAPL", json={})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_holding_not_found(client, mock_market_data):
    response = await client.patch("/api/v1/portfolio/NONEXIST", json={"quantity": 1.0})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_holding(client, mock_market_data):
    payload = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "type": "stock",
        "quantity": 10,
        "avg_buy_price": 150.0,
    }
    await client.post("/api/v1/portfolio/", json=payload)

    response = await client.delete("/api/v1/portfolio/AAPL")
    assert response.status_code == 204

    # Verify it's gone
    response = await client.get("/api/v1/portfolio/AAPL")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_holding_not_found(client, mock_market_data):
    response = await client.delete("/api/v1/portfolio/NONEXIST")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_portfolio_total_value(client, mock_market_data):
    await client.post("/api/v1/portfolio/", json={
        "symbol": "AAPL", "name": "Apple", "type": "stock",
        "quantity": 10, "avg_buy_price": 100.0,
    })
    await client.post("/api/v1/portfolio/", json={
        "symbol": "GOOG", "name": "Google", "type": "stock",
        "quantity": 5, "avg_buy_price": 200.0,
    })

    response = await client.get("/api/v1/portfolio/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_value"] == 2000.0  # 10*100 + 5*200
    assert len(data["holdings"]) == 2


@pytest.mark.asyncio
async def test_add_holding_validation_errors(client, mock_market_data):
    # Missing required fields
    response = await client.post("/api/v1/portfolio/", json={})
    assert response.status_code == 422

    # Invalid quantity (zero)
    response = await client.post("/api/v1/portfolio/", json={
        "symbol": "AAPL", "name": "Apple", "type": "stock",
        "quantity": 0, "avg_buy_price": 100.0,
    })
    assert response.status_code == 422

    # Invalid asset type
    response = await client.post("/api/v1/portfolio/", json={
        "symbol": "AAPL", "name": "Apple", "type": "invalid",
        "quantity": 10, "avg_buy_price": 100.0,
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_symbol_case_insensitive(client, mock_market_data):
    await client.post("/api/v1/portfolio/", json={
        "symbol": "aapl", "name": "Apple", "type": "stock",
        "quantity": 10, "avg_buy_price": 100.0,
    })

    response = await client.get("/api/v1/portfolio/AAPL")
    assert response.status_code == 200
    assert response.json()["asset"]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_portfolio_with_live_prices(client, mock_market_data):
    """Test that live market prices are used when available."""
    from unittest.mock import AsyncMock

    mock_market_data.get_quote = AsyncMock(return_value={
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "price": 200.0,
        "change_percent": 1.5,
        "volume": 50000000,
    })

    await client.post("/api/v1/portfolio/", json={
        "symbol": "AAPL", "name": "Apple Inc.", "type": "stock",
        "quantity": 10, "avg_buy_price": 150.0,
    })

    response = await client.get("/api/v1/portfolio/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["asset"]["price"] == 200.0
    assert data["current_value"] == 2000.0
    assert data["unrealized_pnl"] == 500.0
    assert data["unrealized_pnl_percent"] == pytest.approx(33.33, abs=0.01)
