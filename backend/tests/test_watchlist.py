import pytest


@pytest.mark.asyncio
async def test_get_empty_watchlists(client):
    response = await client.get("/api/v1/watchlists/")
    assert response.status_code == 200
    data = response.json()
    assert data["watchlists"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_create_watchlist(client):
    response = await client.post("/api/v1/watchlists/", json={"name": "Tech Stocks"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Tech Stocks"
    assert data["assets"] == []
    assert "id" in data


@pytest.mark.asyncio
async def test_get_watchlist_by_id(client):
    create_resp = await client.post("/api/v1/watchlists/", json={"name": "My List"})
    wl_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/watchlists/{wl_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "My List"


@pytest.mark.asyncio
async def test_get_watchlist_not_found(client):
    response = await client.get("/api/v1/watchlists/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_watchlist_name(client):
    create_resp = await client.post("/api/v1/watchlists/", json={"name": "Old Name"})
    wl_id = create_resp.json()["id"]

    response = await client.patch(f"/api/v1/watchlists/{wl_id}", json={"name": "New Name"})
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_update_watchlist_not_found(client):
    response = await client.patch("/api/v1/watchlists/bad-id", json={"name": "X"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_watchlist(client):
    create_resp = await client.post("/api/v1/watchlists/", json={"name": "To Delete"})
    wl_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/watchlists/{wl_id}")
    assert response.status_code == 204

    # Verify it's gone
    response = await client.get(f"/api/v1/watchlists/{wl_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_watchlist_not_found(client):
    response = await client.delete("/api/v1/watchlists/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_asset_to_watchlist(client):
    create_resp = await client.post("/api/v1/watchlists/", json={"name": "Tech"})
    wl_id = create_resp.json()["id"]

    response = await client.post(f"/api/v1/watchlists/{wl_id}/assets", json={
        "symbol": "AAPL", "name": "Apple Inc.", "type": "stock",
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["assets"]) == 1
    assert data["assets"][0]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_add_duplicate_asset_to_watchlist(client):
    create_resp = await client.post("/api/v1/watchlists/", json={"name": "Tech"})
    wl_id = create_resp.json()["id"]

    payload = {"symbol": "AAPL", "name": "Apple Inc.", "type": "stock"}
    await client.post(f"/api/v1/watchlists/{wl_id}/assets", json=payload)
    response = await client.post(f"/api/v1/watchlists/{wl_id}/assets", json=payload)

    # Should not duplicate the asset
    assert response.status_code == 200
    assert len(response.json()["assets"]) == 1


@pytest.mark.asyncio
async def test_add_asset_watchlist_not_found(client):
    response = await client.post("/api/v1/watchlists/bad-id/assets", json={
        "symbol": "AAPL", "name": "Apple", "type": "stock",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_remove_asset_from_watchlist(client):
    create_resp = await client.post("/api/v1/watchlists/", json={"name": "Tech"})
    wl_id = create_resp.json()["id"]

    await client.post(f"/api/v1/watchlists/{wl_id}/assets", json={
        "symbol": "AAPL", "name": "Apple Inc.", "type": "stock",
    })

    response = await client.delete(f"/api/v1/watchlists/{wl_id}/assets/AAPL")
    assert response.status_code == 200
    assert len(response.json()["assets"]) == 0


@pytest.mark.asyncio
async def test_remove_asset_watchlist_not_found(client):
    response = await client.delete("/api/v1/watchlists/bad-id/assets/AAPL")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_multiple_watchlists(client):
    await client.post("/api/v1/watchlists/", json={"name": "Tech"})
    await client.post("/api/v1/watchlists/", json={"name": "Crypto"})
    await client.post("/api/v1/watchlists/", json={"name": "ETFs"})

    response = await client.get("/api/v1/watchlists/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["watchlists"]) == 3


@pytest.mark.asyncio
async def test_multiple_assets_in_watchlist(client):
    create_resp = await client.post("/api/v1/watchlists/", json={"name": "Mixed"})
    wl_id = create_resp.json()["id"]

    await client.post(f"/api/v1/watchlists/{wl_id}/assets", json={
        "symbol": "AAPL", "name": "Apple", "type": "stock",
    })
    await client.post(f"/api/v1/watchlists/{wl_id}/assets", json={
        "symbol": "BTC", "name": "Bitcoin", "type": "crypto",
    })
    await client.post(f"/api/v1/watchlists/{wl_id}/assets", json={
        "symbol": "GLD", "name": "Gold ETF", "type": "etf",
    })

    response = await client.get(f"/api/v1/watchlists/{wl_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["assets"]) == 3
    symbols = {a["symbol"] for a in data["assets"]}
    assert symbols == {"AAPL", "BTC", "GLD"}


@pytest.mark.asyncio
async def test_create_watchlist_validation(client):
    # Empty name
    response = await client.post("/api/v1/watchlists/", json={"name": ""})
    assert response.status_code == 422

    # Missing name
    response = await client.post("/api/v1/watchlists/", json={})
    assert response.status_code == 422
