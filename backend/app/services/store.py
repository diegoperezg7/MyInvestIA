"""Data store for portfolio, watchlists, and AI memory.

Supports two backends:
- InMemoryStore: Default, no external dependencies (dict-based, non-persistent)
- SupabaseStore: PostgreSQL-backed persistent storage via Supabase

The active backend is selected automatically based on whether SUPABASE_URL
and SUPABASE_KEY are configured in the environment.
"""

import logging
import uuid

from app.config import settings

logger = logging.getLogger(__name__)


class InMemoryStore:
    """In-memory data store (default when Supabase is not configured)."""

    def __init__(self):
        self.holdings: dict[str, dict] = {}  # keyed by symbol
        self.watchlists: dict[str, dict] = {}  # keyed by watchlist id
        self._ai_memories: list[dict] = []

    # --- Portfolio ---

    def get_holdings(self) -> list[dict]:
        return list(self.holdings.values())

    def get_holding(self, symbol: str) -> dict | None:
        return self.holdings.get(symbol.upper())

    def add_holding(self, symbol: str, name: str, asset_type: str, quantity: float, avg_buy_price: float) -> dict:
        symbol = symbol.upper()
        if symbol in self.holdings:
            existing = self.holdings[symbol]
            old_qty = existing["quantity"]
            old_avg = existing["avg_buy_price"]
            new_qty = old_qty + quantity
            new_avg = ((old_avg * old_qty) + (avg_buy_price * quantity)) / new_qty
            existing["quantity"] = new_qty
            existing["avg_buy_price"] = new_avg
            return existing

        holding = {
            "symbol": symbol,
            "name": name,
            "type": asset_type,
            "quantity": quantity,
            "avg_buy_price": avg_buy_price,
        }
        self.holdings[symbol] = holding
        return holding

    def update_holding(self, symbol: str, quantity: float | None = None, avg_buy_price: float | None = None) -> dict | None:
        symbol = symbol.upper()
        holding = self.holdings.get(symbol)
        if not holding:
            return None
        if quantity is not None:
            holding["quantity"] = quantity
        if avg_buy_price is not None:
            holding["avg_buy_price"] = avg_buy_price
        return holding

    def delete_holding(self, symbol: str) -> bool:
        symbol = symbol.upper()
        return self.holdings.pop(symbol, None) is not None

    # --- Watchlists ---

    def get_watchlists(self) -> list[dict]:
        return list(self.watchlists.values())

    def get_watchlist(self, watchlist_id: str) -> dict | None:
        return self.watchlists.get(watchlist_id)

    def create_watchlist(self, name: str) -> dict:
        wl_id = str(uuid.uuid4())
        watchlist = {"id": wl_id, "name": name, "assets": []}
        self.watchlists[wl_id] = watchlist
        return watchlist

    def update_watchlist(self, watchlist_id: str, name: str) -> dict | None:
        watchlist = self.watchlists.get(watchlist_id)
        if not watchlist:
            return None
        watchlist["name"] = name
        return watchlist

    def delete_watchlist(self, watchlist_id: str) -> bool:
        return self.watchlists.pop(watchlist_id, None) is not None

    def add_asset_to_watchlist(self, watchlist_id: str, symbol: str, name: str, asset_type: str) -> dict | None:
        watchlist = self.watchlists.get(watchlist_id)
        if not watchlist:
            return None
        symbol = symbol.upper()
        for asset in watchlist["assets"]:
            if asset["symbol"] == symbol:
                return watchlist  # already exists
        watchlist["assets"].append({
            "symbol": symbol,
            "name": name,
            "type": asset_type,
            "price": 0.0,
            "change_percent": 0.0,
            "volume": 0.0,
        })
        return watchlist

    def remove_asset_from_watchlist(self, watchlist_id: str, symbol: str) -> dict | None:
        watchlist = self.watchlists.get(watchlist_id)
        if not watchlist:
            return None
        symbol = symbol.upper()
        watchlist["assets"] = [a for a in watchlist["assets"] if a["symbol"] != symbol]
        return watchlist

    # --- AI Memory ---

    def save_memory(self, category: str, content: str, metadata: dict | None = None) -> dict:
        entry = {
            "id": str(uuid.uuid4()),
            "category": category,
            "content": content,
            "metadata": metadata or {},
        }
        self._ai_memories.insert(0, entry)
        return entry

    def get_memories(self, category: str | None = None, limit: int = 50) -> list[dict]:
        memories = self._ai_memories
        if category:
            memories = [m for m in memories if m["category"] == category]
        return memories[:limit]

    def delete_memory(self, memory_id: str) -> bool:
        for i, m in enumerate(self._ai_memories):
            if m["id"] == memory_id:
                self._ai_memories.pop(i)
                return True
        return False


def _create_store() -> InMemoryStore:
    """Create the appropriate store backend based on configuration."""
    if settings.supabase_url and settings.supabase_key:
        try:
            from app.services.supabase_store import SupabaseStore
            logger.info("Supabase configured — using SupabaseStore for persistence")
            return SupabaseStore()
        except Exception as e:
            logger.warning("Failed to initialize SupabaseStore, falling back to InMemoryStore: %s", e)
    return InMemoryStore()


# Singleton store instance — automatically selects backend
store = _create_store()
