"""Supabase-backed data store for portfolio, watchlists, and AI memory.

Provides the same interface as InMemoryStore but persists data in Supabase
PostgreSQL. Falls back to InMemoryStore when Supabase is not configured.

Required Supabase tables (create via SQL editor):

-- Holdings table
CREATE TABLE IF NOT EXISTS holdings (
    symbol TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    quantity REAL NOT NULL,
    avg_buy_price REAL NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Watchlists table
CREATE TABLE IF NOT EXISTS watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Watchlist assets table
CREATE TABLE IF NOT EXISTS watchlist_assets (
    watchlist_id UUID REFERENCES watchlists(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    PRIMARY KEY (watchlist_id, symbol)
);

-- AI memory table
CREATE TABLE IF NOT EXISTS ai_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ai_memory_category ON ai_memory(category);
"""

import logging
import uuid

from app.config import settings

logger = logging.getLogger(__name__)


class SupabaseStore:
    """Supabase-backed store with the same interface as InMemoryStore."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from supabase import create_client
            self._client = create_client(settings.supabase_url, settings.supabase_key)
        return self._client

    @property
    def configured(self) -> bool:
        return bool(settings.supabase_url and settings.supabase_key)

    # --- Portfolio ---

    def get_holdings(self) -> list[dict]:
        try:
            result = self._get_client().table("holdings").select("*").execute()
            return result.data or []
        except Exception as e:
            logger.warning("Supabase get_holdings failed: %s", e)
            return []

    def get_holding(self, symbol: str) -> dict | None:
        try:
            result = (
                self._get_client()
                .table("holdings")
                .select("*")
                .eq("symbol", symbol.upper())
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase get_holding failed for %s: %s", symbol, e)
            return None

    def add_holding(
        self, symbol: str, name: str, asset_type: str, quantity: float, avg_buy_price: float
    ) -> dict:
        symbol = symbol.upper()
        existing = self.get_holding(symbol)
        client = self._get_client()

        if existing:
            old_qty = existing["quantity"]
            old_avg = existing["avg_buy_price"]
            new_qty = old_qty + quantity
            new_avg = ((old_avg * old_qty) + (avg_buy_price * quantity)) / new_qty
            result = (
                client.table("holdings")
                .update({"quantity": new_qty, "avg_buy_price": new_avg})
                .eq("symbol", symbol)
                .execute()
            )
            return result.data[0] if result.data else {"symbol": symbol, "name": name, "type": asset_type, "quantity": new_qty, "avg_buy_price": new_avg}

        holding = {
            "symbol": symbol,
            "name": name,
            "type": asset_type,
            "quantity": quantity,
            "avg_buy_price": avg_buy_price,
        }
        result = client.table("holdings").insert(holding).execute()
        return result.data[0] if result.data else holding

    def update_holding(
        self, symbol: str, quantity: float | None = None, avg_buy_price: float | None = None
    ) -> dict | None:
        symbol = symbol.upper()
        existing = self.get_holding(symbol)
        if not existing:
            return None

        updates = {}
        if quantity is not None:
            updates["quantity"] = quantity
        if avg_buy_price is not None:
            updates["avg_buy_price"] = avg_buy_price

        if updates:
            result = (
                self._get_client()
                .table("holdings")
                .update(updates)
                .eq("symbol", symbol)
                .execute()
            )
            return result.data[0] if result.data else {**existing, **updates}
        return existing

    def delete_holding(self, symbol: str) -> bool:
        symbol = symbol.upper()
        try:
            result = (
                self._get_client()
                .table("holdings")
                .delete()
                .eq("symbol", symbol)
                .execute()
            )
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            logger.warning("Supabase delete_holding failed for %s: %s", symbol, e)
            return False

    # --- Watchlists ---

    def get_watchlists(self) -> list[dict]:
        try:
            client = self._get_client()
            result = client.table("watchlists").select("*").execute()
            watchlists = []
            for wl in (result.data or []):
                assets_result = (
                    client.table("watchlist_assets")
                    .select("*")
                    .eq("watchlist_id", wl["id"])
                    .execute()
                )
                assets = [
                    {
                        "symbol": a["symbol"],
                        "name": a["name"],
                        "type": a["type"],
                        "price": 0.0,
                        "change_percent": 0.0,
                        "volume": 0.0,
                    }
                    for a in (assets_result.data or [])
                ]
                watchlists.append({"id": wl["id"], "name": wl["name"], "assets": assets})
            return watchlists
        except Exception as e:
            logger.warning("Supabase get_watchlists failed: %s", e)
            return []

    def get_watchlist(self, watchlist_id: str) -> dict | None:
        try:
            client = self._get_client()
            result = (
                client.table("watchlists")
                .select("*")
                .eq("id", watchlist_id)
                .execute()
            )
            if not result.data:
                return None
            wl = result.data[0]
            assets_result = (
                client.table("watchlist_assets")
                .select("*")
                .eq("watchlist_id", watchlist_id)
                .execute()
            )
            assets = [
                {
                    "symbol": a["symbol"],
                    "name": a["name"],
                    "type": a["type"],
                    "price": 0.0,
                    "change_percent": 0.0,
                    "volume": 0.0,
                }
                for a in (assets_result.data or [])
            ]
            return {"id": wl["id"], "name": wl["name"], "assets": assets}
        except Exception as e:
            logger.warning("Supabase get_watchlist failed for %s: %s", watchlist_id, e)
            return None

    def create_watchlist(self, name: str) -> dict:
        wl_id = str(uuid.uuid4())
        try:
            result = (
                self._get_client()
                .table("watchlists")
                .insert({"id": wl_id, "name": name})
                .execute()
            )
            wl = result.data[0] if result.data else {"id": wl_id, "name": name}
            return {"id": wl["id"], "name": wl["name"], "assets": []}
        except Exception as e:
            logger.warning("Supabase create_watchlist failed: %s", e)
            return {"id": wl_id, "name": name, "assets": []}

    def update_watchlist(self, watchlist_id: str, name: str) -> dict | None:
        existing = self.get_watchlist(watchlist_id)
        if not existing:
            return None
        try:
            self._get_client().table("watchlists").update({"name": name}).eq("id", watchlist_id).execute()
            existing["name"] = name
            return existing
        except Exception as e:
            logger.warning("Supabase update_watchlist failed: %s", e)
            return None

    def delete_watchlist(self, watchlist_id: str) -> bool:
        try:
            result = (
                self._get_client()
                .table("watchlists")
                .delete()
                .eq("id", watchlist_id)
                .execute()
            )
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            logger.warning("Supabase delete_watchlist failed: %s", e)
            return False

    def add_asset_to_watchlist(
        self, watchlist_id: str, symbol: str, name: str, asset_type: str
    ) -> dict | None:
        watchlist = self.get_watchlist(watchlist_id)
        if not watchlist:
            return None
        symbol = symbol.upper()
        for asset in watchlist["assets"]:
            if asset["symbol"] == symbol:
                return watchlist
        try:
            self._get_client().table("watchlist_assets").insert({
                "watchlist_id": watchlist_id,
                "symbol": symbol,
                "name": name,
                "type": asset_type,
            }).execute()
            watchlist["assets"].append({
                "symbol": symbol, "name": name, "type": asset_type,
                "price": 0.0, "change_percent": 0.0, "volume": 0.0,
            })
            return watchlist
        except Exception as e:
            logger.warning("Supabase add_asset failed: %s", e)
            return None

    def remove_asset_from_watchlist(self, watchlist_id: str, symbol: str) -> dict | None:
        watchlist = self.get_watchlist(watchlist_id)
        if not watchlist:
            return None
        symbol = symbol.upper()
        try:
            self._get_client().table("watchlist_assets").delete().eq(
                "watchlist_id", watchlist_id
            ).eq("symbol", symbol).execute()
            watchlist["assets"] = [a for a in watchlist["assets"] if a["symbol"] != symbol]
            return watchlist
        except Exception as e:
            logger.warning("Supabase remove_asset failed: %s", e)
            return None

    # --- AI Memory ---

    def save_memory(self, category: str, content: str, metadata: dict | None = None) -> dict:
        """Save an AI memory entry (e.g., past alert, user preference, interaction)."""
        entry = {
            "id": str(uuid.uuid4()),
            "category": category,
            "content": content,
            "metadata": metadata or {},
        }
        try:
            result = self._get_client().table("ai_memory").insert(entry).execute()
            return result.data[0] if result.data else entry
        except Exception as e:
            logger.warning("Supabase save_memory failed: %s", e)
            return entry

    def get_memories(self, category: str | None = None, limit: int = 50) -> list[dict]:
        """Retrieve AI memory entries, optionally filtered by category."""
        try:
            query = self._get_client().table("ai_memory").select("*")
            if category:
                query = query.eq("category", category)
            result = query.order("created_at", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.warning("Supabase get_memories failed: %s", e)
            return []

    def delete_memory(self, memory_id: str) -> bool:
        """Delete an AI memory entry."""
        try:
            result = self._get_client().table("ai_memory").delete().eq("id", memory_id).execute()
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            logger.warning("Supabase delete_memory failed: %s", e)
            return False
