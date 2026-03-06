"""Data store for portfolio, watchlists, and AI memory.

Supports two backends:
- InMemoryStore: Default, no external dependencies (dict-based, non-persistent)
- SupabaseStore: PostgreSQL-backed persistent storage via Supabase

All methods require a user_id parameter for multi-user isolation.
Supports multi-tenancy when enable_multitenant is True.
"""

import logging
import uuid

from app.config import settings

logger = logging.getLogger(__name__)


class InMemoryStore:
    """In-memory data store (default when Supabase is not configured).

    Data is keyed by (tenant_id, user_id) for multi-tenant + multi-user support.
    """

    def __init__(self):
        self._tenants: dict[str, dict] = {}  # tenant_id -> { users, holdings, ... }
        self._enable_multitenant = getattr(settings, "enable_multitenant", False)
        self._default_tenant = getattr(settings, "default_tenant_id", "default")

    def _get_tenant_data(self, tenant_id: str) -> dict:
        """Get or create tenant data structure."""
        if tenant_id not in self._tenants:
            self._tenants[tenant_id] = {
                "holdings": {},  # user_id -> symbol -> holding
                "watchlists": {},  # user_id -> wl_id -> watchlist
                "ai_memories": {},  # user_id -> [memories]
                "connections": {},  # user_id -> conn_id -> connection
                "sync_history": {},  # user_id -> [history]
                "synced_holdings": {},  # user_id -> key -> holding
                "users": set(),  # user_ids that belong to this tenant
            }
        return self._tenants[tenant_id]

    def _normalize_tenant_user(
        self, tenant_id: str | None, user_id: str
    ) -> tuple[str, str]:
        """Normalize tenant_id and user_id based on multi-tenancy setting.

        If tenant_id is None, uses default tenant (backwards compatible).
        """
        if tenant_id:
            return tenant_id, user_id
        return self._default_tenant, user_id

    def get_tenants(self) -> list[dict]:
        """Get list of all tenants."""
        return [
            {"id": tid, "user_count": len(data.get("users", set()))}
            for tid, data in self._tenants.items()
        ]

    def create_tenant(self, tenant_id: str, name: str = "") -> dict:
        """Create a new tenant."""
        self._tenants[tenant_id] = {
            "name": name,
            "holdings": {},
            "watchlists": {},
            "ai_memories": {},
            "connections": {},
            "sync_history": {},
            "synced_holdings": {},
            "users": set(),
        }
        return {"id": tenant_id, "name": name}

    def add_user_to_tenant(self, tenant_id: str, user_id: str) -> bool:
        """Assign a user to a tenant."""
        tenant = self._get_tenant_data(tenant_id)
        tenant["users"].add(user_id)
        return True

    # --- Portfolio ---

    def get_holdings(self, user_id: str, tenant_id: str | None = None) -> list[dict]:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        manual = list(tenant["holdings"].get(user_id, {}).values())
        for h in manual:
            h.setdefault("source", "manual")
            h.setdefault("connection_id", None)
        synced = list(tenant["synced_holdings"].get(user_id, {}).values())
        return manual + synced

    def get_holding(
        self, user_id: str, symbol: str, tenant_id: str | None = None
    ) -> dict | None:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        return (
            self._get_tenant_data(tenant_id)["holdings"]
            .get(user_id, {})
            .get(symbol.upper())
        )

    def add_holding(
        self,
        user_id: str,
        symbol: str,
        name: str,
        asset_type: str,
        quantity: float,
        avg_buy_price: float,
        tenant_id: str | None = None,
    ) -> dict:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        tenant["users"].add(user_id)
        symbol = symbol.upper()
        user_holdings = tenant["holdings"].setdefault(user_id, {})
        if symbol in user_holdings:
            existing = user_holdings[symbol]
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
        user_holdings[symbol] = holding
        return holding

    def update_holding(
        self,
        user_id: str,
        symbol: str,
        quantity: float | None = None,
        avg_buy_price: float | None = None,
        tenant_id: str | None = None,
    ) -> dict | None:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        symbol = symbol.upper()
        holding = tenant["holdings"].get(user_id, {}).get(symbol)
        if not holding:
            return None
        if quantity is not None:
            holding["quantity"] = quantity
        if avg_buy_price is not None:
            holding["avg_buy_price"] = avg_buy_price
        return holding

    def delete_holding(
        self, user_id: str, symbol: str, tenant_id: str | None = None
    ) -> bool:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        symbol = symbol.upper()
        return tenant["holdings"].get(user_id, {}).pop(symbol, None) is not None

    # --- Watchlists ---

    def get_watchlists(self, user_id: str, tenant_id: str | None = None) -> list[dict]:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        return list(tenant["watchlists"].get(user_id, {}).values())

    def get_watchlist(
        self, user_id: str, watchlist_id: str, tenant_id: str | None = None
    ) -> dict | None:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        return tenant["watchlists"].get(user_id, {}).get(watchlist_id)

    def create_watchlist(
        self, user_id: str, name: str, tenant_id: str | None = None
    ) -> dict:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        tenant["users"].add(user_id)
        wl_id = str(uuid.uuid4())
        watchlist = {"id": wl_id, "name": name, "assets": []}
        tenant["watchlists"].setdefault(user_id, {})[wl_id] = watchlist
        return watchlist

    def update_watchlist(
        self, user_id: str, watchlist_id: str, name: str, tenant_id: str | None = None
    ) -> dict | None:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        watchlist = tenant["watchlists"].get(user_id, {}).get(watchlist_id)
        if not watchlist:
            return None
        watchlist["name"] = name
        return watchlist

    def delete_watchlist(
        self, user_id: str, watchlist_id: str, tenant_id: str | None = None
    ) -> bool:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        return tenant["watchlists"].get(user_id, {}).pop(watchlist_id, None) is not None

    def add_asset_to_watchlist(
        self,
        user_id: str,
        watchlist_id: str,
        symbol: str,
        name: str,
        asset_type: str,
        tenant_id: str | None = None,
    ) -> dict | None:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        watchlist = tenant["watchlists"].get(user_id, {}).get(watchlist_id)
        if not watchlist:
            return None
        symbol = symbol.upper()
        for asset in watchlist["assets"]:
            if asset["symbol"] == symbol:
                return watchlist
        watchlist["assets"].append(
            {
                "symbol": symbol,
                "name": name,
                "type": asset_type,
                "price": 0.0,
                "change_percent": 0.0,
                "volume": 0.0,
            }
        )
        return watchlist

    def remove_asset_from_watchlist(
        self, user_id: str, watchlist_id: str, symbol: str, tenant_id: str | None = None
    ) -> dict | None:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        watchlist = tenant["watchlists"].get(user_id, {}).get(watchlist_id)
        if not watchlist:
            return None
        symbol = symbol.upper()
        watchlist["assets"] = [a for a in watchlist["assets"] if a["symbol"] != symbol]
        return watchlist

    # --- AI Memory ---

    def save_memory(
        self,
        user_id: str,
        category: str,
        content: str,
        metadata: dict | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        tenant["users"].add(user_id)
        entry = {
            "id": str(uuid.uuid4()),
            "category": category,
            "content": content,
            "metadata": metadata or {},
        }
        tenant["ai_memories"].setdefault(user_id, []).insert(0, entry)
        return entry

    def get_memories(
        self,
        user_id: str,
        category: str | None = None,
        limit: int = 50,
        tenant_id: str | None = None,
    ) -> list[dict]:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        memories = tenant["ai_memories"].get(user_id, [])
        if category:
            memories = [m for m in memories if m["category"] == category]
        return memories[:limit]

    def delete_memory(
        self, user_id: str, memory_id: str, tenant_id: str | None = None
    ) -> bool:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        memories = tenant["ai_memories"].get(user_id, [])
        for i, m in enumerate(memories):
            if m["id"] == memory_id:
                memories.pop(i)
                return True
        return False

    # --- Synced Holdings ---

    def upsert_synced_holding(
        self,
        user_id: str,
        symbol: str,
        name: str,
        asset_type: str,
        quantity: float,
        avg_buy_price: float,
        source: str,
        connection_id: str,
        tenant_id: str | None = None,
    ) -> dict:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        tenant["users"].add(user_id)
        key = f"{symbol.upper()}:{connection_id}"
        user_synced = tenant["synced_holdings"].setdefault(user_id, {})
        holding = {
            "id": user_synced.get(key, {}).get("id", str(uuid.uuid4())),
            "symbol": symbol.upper(),
            "name": name,
            "type": asset_type,
            "quantity": quantity,
            "avg_buy_price": avg_buy_price,
            "source": source,
            "connection_id": connection_id,
        }
        user_synced[key] = holding
        return holding

    def delete_synced_holding(
        self,
        user_id: str,
        symbol: str,
        connection_id: str,
        tenant_id: str | None = None,
    ) -> bool:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        key = f"{symbol.upper()}:{connection_id}"
        return tenant["synced_holdings"].get(user_id, {}).pop(key, None) is not None

    def delete_holdings_by_connection(
        self, user_id: str, connection_id: str, tenant_id: str | None = None
    ) -> int:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        user_synced = tenant["synced_holdings"].get(user_id, {})
        keys_to_delete = [
            k for k, v in user_synced.items() if v.get("connection_id") == connection_id
        ]
        for k in keys_to_delete:
            del user_synced[k]
        return len(keys_to_delete)

    def get_holdings_by_connection(
        self, user_id: str, connection_id: str, tenant_id: str | None = None
    ) -> list[dict]:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        return [
            v
            for v in tenant["synced_holdings"].get(user_id, {}).values()
            if v.get("connection_id") == connection_id
        ]

    # --- Connections ---

    def get_connections(self, user_id: str, tenant_id: str | None = None) -> list[dict]:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        return list(tenant["connections"].get(user_id, {}).values())

    def get_connection(
        self, user_id: str, connection_id: str, tenant_id: str | None = None
    ) -> dict | None:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        return tenant["connections"].get(user_id, {}).get(connection_id)

    def create_connection(
        self, user_id: str, data: dict, tenant_id: str | None = None
    ) -> dict:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        tenant["users"].add(user_id)
        tenant["connections"].setdefault(user_id, {})[data["id"]] = data
        return data

    def update_connection(
        self, user_id: str, connection_id: str, data: dict, tenant_id: str | None = None
    ) -> dict | None:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        conn = tenant["connections"].get(user_id, {}).get(connection_id)
        if not conn:
            return None
        conn.update(data)
        return conn

    def delete_connection(
        self, user_id: str, connection_id: str, tenant_id: str | None = None
    ) -> bool:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        return (
            tenant["connections"].get(user_id, {}).pop(connection_id, None) is not None
        )

    # --- Sync History ---

    def add_sync_history(
        self, user_id: str, data: dict, tenant_id: str | None = None
    ) -> dict:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        tenant["sync_history"].setdefault(user_id, []).insert(0, data)
        return data

    def update_sync_history(
        self, user_id: str, sync_id: str, data: dict, tenant_id: str | None = None
    ) -> dict | None:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        for entry in tenant["sync_history"].get(user_id, []):
            if entry.get("id") == sync_id:
                entry.update(data)
                return entry
        return None

    def get_sync_history(
        self,
        user_id: str,
        connection_id: str,
        limit: int = 20,
        tenant_id: str | None = None,
    ) -> list[dict]:
        tenant_id, user_id = self._normalize_tenant_user(tenant_id, user_id)
        tenant = self._get_tenant_data(tenant_id)
        return [
            s
            for s in tenant["sync_history"].get(user_id, [])
            if s.get("connection_id") == connection_id
        ][:limit]


def _create_store() -> InMemoryStore:
    """Create the appropriate store backend based on configuration."""
    if settings.supabase_url and settings.supabase_key:
        try:
            from app.services.supabase_store import SupabaseStore

            logger.info("Supabase configured — using SupabaseStore for persistence")
            return SupabaseStore()
        except Exception as e:
            logger.warning(
                "Failed to initialize SupabaseStore, falling back to InMemoryStore: %s",
                e,
            )
    return InMemoryStore()


# Singleton store instance — automatically selects backend
store = _create_store()
