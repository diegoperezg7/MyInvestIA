"""Tests for AI memory endpoints and store memory methods."""

import pytest

from app.services.store import store


class TestStoreMemoryMethods:
    """Tests for InMemoryStore AI memory methods."""

    def test_save_memory(self):
        entry = store.save_memory("user_preference", "Prefers tech stocks")
        assert entry["category"] == "user_preference"
        assert entry["content"] == "Prefers tech stocks"
        assert entry["id"]
        assert entry["metadata"] == {}

    def test_save_memory_with_metadata(self):
        entry = store.save_memory("market_note", "BTC bullish", {"source": "chat"})
        assert entry["metadata"] == {"source": "chat"}

    def test_get_memories_all(self):
        store.save_memory("interaction", "Asked about AAPL")
        store.save_memory("user_preference", "Risk-averse investor")
        memories = store.get_memories()
        assert len(memories) == 2

    def test_get_memories_by_category(self):
        store.save_memory("interaction", "Asked about AAPL")
        store.save_memory("user_preference", "Risk-averse investor")
        store.save_memory("interaction", "Asked about BTC")
        memories = store.get_memories(category="interaction")
        assert len(memories) == 2
        assert all(m["category"] == "interaction" for m in memories)

    def test_get_memories_limit(self):
        for i in range(10):
            store.save_memory("interaction", f"Message {i}")
        memories = store.get_memories(limit=3)
        assert len(memories) == 3

    def test_get_memories_most_recent_first(self):
        store.save_memory("interaction", "First")
        store.save_memory("interaction", "Second")
        memories = store.get_memories()
        assert memories[0]["content"] == "Second"
        assert memories[1]["content"] == "First"

    def test_delete_memory(self):
        entry = store.save_memory("interaction", "Test")
        assert store.delete_memory(entry["id"]) is True
        assert store.get_memories() == []

    def test_delete_memory_not_found(self):
        assert store.delete_memory("nonexistent-id") is False


class TestMemoryRouter:
    """Tests for /api/v1/memory endpoints."""

    @pytest.mark.asyncio
    async def test_save_memory_endpoint(self, client):
        response = await client.post("/api/v1/memory/", json={
            "category": "user_preference",
            "content": "Interested in AI stocks",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["category"] == "user_preference"
        assert data["content"] == "Interested in AI stocks"
        assert data["id"]

    @pytest.mark.asyncio
    async def test_save_memory_with_metadata(self, client):
        response = await client.post("/api/v1/memory/", json={
            "category": "market_note",
            "content": "BTC halving approaching",
            "metadata": {"source": "chat", "symbol": "BTC"},
        })
        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["source"] == "chat"

    @pytest.mark.asyncio
    async def test_get_memories_endpoint(self, client):
        await client.post("/api/v1/memory/", json={
            "category": "interaction",
            "content": "Asked about AAPL",
        })
        await client.post("/api/v1/memory/", json={
            "category": "user_preference",
            "content": "Prefers growth stocks",
        })
        response = await client.get("/api/v1/memory/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["memories"]) == 2

    @pytest.mark.asyncio
    async def test_get_memories_filter_by_category(self, client):
        await client.post("/api/v1/memory/", json={
            "category": "interaction",
            "content": "Asked about AAPL",
        })
        await client.post("/api/v1/memory/", json={
            "category": "user_preference",
            "content": "Prefers growth stocks",
        })
        response = await client.get("/api/v1/memory/?category=interaction")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["memories"][0]["category"] == "interaction"

    @pytest.mark.asyncio
    async def test_get_memories_with_limit(self, client):
        for i in range(5):
            await client.post("/api/v1/memory/", json={
                "category": "interaction",
                "content": f"Message {i}",
            })
        response = await client.get("/api/v1/memory/?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_delete_memory_endpoint(self, client):
        resp = await client.post("/api/v1/memory/", json={
            "category": "interaction",
            "content": "To be deleted",
        })
        memory_id = resp.json()["id"]
        delete_resp = await client.delete(f"/api/v1/memory/{memory_id}")
        assert delete_resp.status_code == 200
        assert delete_resp.json()["deleted"] is True

        # Verify deleted
        get_resp = await client.get("/api/v1/memory/")
        assert get_resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_delete_memory_not_found(self, client):
        response = await client.delete("/api/v1/memory/nonexistent-id")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_save_memory_validation_empty_category(self, client):
        response = await client.post("/api/v1/memory/", json={
            "category": "",
            "content": "Some content",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_save_memory_validation_empty_content(self, client):
        response = await client.post("/api/v1/memory/", json={
            "category": "interaction",
            "content": "",
        })
        assert response.status_code == 422
