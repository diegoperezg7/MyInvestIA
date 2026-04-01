"""Supabase-backed data store for portfolio, watchlists, and AI memory.

Multi-user: all operations require a user_id parameter to scope data.
The backend uses the service_role key (bypasses RLS) so we must filter
by user_id explicitly in every query.

Multi-tenancy: optionally use tenant_id parameter. Requires adding tenant_id
column to Supabase tables for full implementation.
"""

import logging
import uuid
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class SupabaseStore:
    """Supabase-backed store — all methods require user_id.

    Supports optional tenant_id for multi-tenancy (requires table modifications).
    """

    def __init__(self):
        self._client = None
        self._workflow_fallback = {
            "inbox_items": {},
            "theses": {},
            "thesis_events": {},
            "alert_rules": {},
            "research_screens": {},
            "research_snapshots": {},
            "connections": {},
            "sync_history": {},
        }

    def _get_client(self):
        if self._client is None:
            from supabase import create_client

            key = settings.supabase_service_key or settings.supabase_key
            self._client = create_client(settings.supabase_url, key)
        return self._client

    @property
    def configured(self) -> bool:
        return bool(
            settings.supabase_url
            and (settings.supabase_service_key or settings.supabase_key)
        )

    def _build_tenant_filter(self, query, tenant_id: Optional[str]):
        """Add tenant filter to query if tenant_id provided and column exists."""
        if tenant_id and settings.enable_multitenant:
            try:
                query = query.eq("tenant_id", tenant_id)
            except Exception:
                pass
        return query

    # --- Portfolio ---

    def get_holdings(self, user_id: str, tenant_id: Optional[str] = None) -> list[dict]:
        try:
            query = (
                self._get_client().table("holdings").select("*").eq("user_id", user_id)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            holdings = result.data or []
            for h in holdings:
                h.setdefault("source", "manual")
                h.setdefault("connection_id", None)
            return holdings
        except Exception as e:
            logger.warning("Supabase get_holdings failed: %s", e)
            return []

    def get_holding(
        self, user_id: str, symbol: str, tenant_id: Optional[str] = None
    ) -> dict | None:
        try:
            query = (
                self._get_client()
                .table("holdings")
                .select("*")
                .eq("user_id", user_id)
                .eq("symbol", symbol.upper())
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase get_holding failed for %s: %s", symbol, e)
            return None

    def add_holding(
        self,
        user_id: str,
        symbol: str,
        name: str,
        asset_type: str,
        quantity: float,
        avg_buy_price: float,
        tenant_id: Optional[str] = None,
    ) -> dict:
        symbol = symbol.upper()
        existing = self.get_holding(user_id, symbol, tenant_id)
        client = self._get_client()

        holding_data = {
            "symbol": symbol,
            "name": name,
            "type": asset_type,
            "quantity": quantity,
            "avg_buy_price": avg_buy_price,
            "user_id": user_id,
        }
        if tenant_id and settings.enable_multitenant:
            holding_data["tenant_id"] = tenant_id

        if existing:
            old_qty = existing["quantity"]
            old_avg = existing["avg_buy_price"]
            new_qty = old_qty + quantity
            new_avg = ((old_avg * old_qty) + (avg_buy_price * quantity)) / new_qty
            result = (
                client.table("holdings")
                .update({"quantity": new_qty, "avg_buy_price": new_avg})
                .eq("user_id", user_id)
                .eq("symbol", symbol)
                .execute()
            )
            return (
                result.data[0]
                if result.data
                else {
                    "symbol": symbol,
                    "name": name,
                    "type": asset_type,
                    "quantity": new_qty,
                    "avg_buy_price": new_avg,
                }
            )

        result = client.table("holdings").insert(holding_data).execute()
        return result.data[0] if result.data else holding_data

    def update_holding(
        self,
        user_id: str,
        symbol: str,
        quantity: float | None = None,
        avg_buy_price: float | None = None,
        tenant_id: Optional[str] = None,
    ) -> dict | None:
        symbol = symbol.upper()
        existing = self.get_holding(user_id, symbol, tenant_id)
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
                .eq("user_id", user_id)
                .eq("symbol", symbol)
                .execute()
            )
            return result.data[0] if result.data else {**existing, **updates}
        return existing

    def delete_holding(
        self, user_id: str, symbol: str, tenant_id: Optional[str] = None
    ) -> bool:
        symbol = symbol.upper()
        try:
            query = (
                self._get_client()
                .table("holdings")
                .delete()
                .eq("user_id", user_id)
                .eq("symbol", symbol)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            logger.warning("Supabase delete_holding failed for %s: %s", symbol, e)
            return False

    # --- Watchlists ---

    def get_watchlists(
        self, user_id: str, tenant_id: Optional[str] = None
    ) -> list[dict]:
        try:
            client = self._get_client()
            result = (
                client.table("watchlists").select("*").eq("user_id", user_id).execute()
            )
            watchlists = []
            for wl in result.data or []:
                assets_result = (
                    client.table("watchlist_assets")
                    .select("*")
                    .eq("watchlist_id", wl["id"])
                    .eq("user_id", user_id)
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
                watchlists.append(
                    {"id": wl["id"], "name": wl["name"], "assets": assets}
                )
            return watchlists
        except Exception as e:
            logger.warning("Supabase get_watchlists failed: %s", e)
            return []

    def get_watchlist(self, user_id: str, watchlist_id: str) -> dict | None:
        try:
            client = self._get_client()
            result = (
                client.table("watchlists")
                .select("*")
                .eq("id", watchlist_id)
                .eq("user_id", user_id)
                .execute()
            )
            if not result.data:
                return None
            wl = result.data[0]
            assets_result = (
                client.table("watchlist_assets")
                .select("*")
                .eq("watchlist_id", watchlist_id)
                .eq("user_id", user_id)
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

    def create_watchlist(self, user_id: str, name: str) -> dict:
        wl_id = str(uuid.uuid4())
        try:
            result = (
                self._get_client()
                .table("watchlists")
                .insert({"id": wl_id, "name": name, "user_id": user_id})
                .execute()
            )
            wl = result.data[0] if result.data else {"id": wl_id, "name": name}
            return {"id": wl["id"], "name": wl["name"], "assets": []}
        except Exception as e:
            logger.warning("Supabase create_watchlist failed: %s", e)
            return {"id": wl_id, "name": name, "assets": []}

    def update_watchlist(
        self, user_id: str, watchlist_id: str, name: str
    ) -> dict | None:
        existing = self.get_watchlist(user_id, watchlist_id)
        if not existing:
            return None
        try:
            self._get_client().table("watchlists").update({"name": name}).eq(
                "id", watchlist_id
            ).eq("user_id", user_id).execute()
            existing["name"] = name
            return existing
        except Exception as e:
            logger.warning("Supabase update_watchlist failed: %s", e)
            return None

    def delete_watchlist(self, user_id: str, watchlist_id: str) -> bool:
        try:
            result = (
                self._get_client()
                .table("watchlists")
                .delete()
                .eq("id", watchlist_id)
                .eq("user_id", user_id)
                .execute()
            )
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            logger.warning("Supabase delete_watchlist failed: %s", e)
            return False

    def add_asset_to_watchlist(
        self,
        user_id: str,
        watchlist_id: str,
        symbol: str,
        name: str,
        asset_type: str,
    ) -> dict | None:
        watchlist = self.get_watchlist(user_id, watchlist_id)
        if not watchlist:
            return None
        symbol = symbol.upper()
        for asset in watchlist["assets"]:
            if asset["symbol"] == symbol:
                return watchlist
        try:
            self._get_client().table("watchlist_assets").insert(
                {
                    "watchlist_id": watchlist_id,
                    "symbol": symbol,
                    "name": name,
                    "type": asset_type,
                    "user_id": user_id,
                }
            ).execute()
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
        except Exception as e:
            logger.warning("Supabase add_asset failed: %s", e)
            return None

    def remove_asset_from_watchlist(
        self, user_id: str, watchlist_id: str, symbol: str
    ) -> dict | None:
        watchlist = self.get_watchlist(user_id, watchlist_id)
        if not watchlist:
            return None
        symbol = symbol.upper()
        try:
            self._get_client().table("watchlist_assets").delete().eq(
                "watchlist_id", watchlist_id
            ).eq("symbol", symbol).eq("user_id", user_id).execute()
            watchlist["assets"] = [
                a for a in watchlist["assets"] if a["symbol"] != symbol
            ]
            return watchlist
        except Exception as e:
            logger.warning("Supabase remove_asset failed: %s", e)
            return None

    # --- AI Memory ---

    def save_memory(
        self,
        user_id: str,
        category: str,
        content: str,
        metadata: dict | None = None,
        tenant_id: Optional[str] = None,
    ) -> dict:
        entry = {
            "id": str(uuid.uuid4()),
            "category": category,
            "content": content,
            "metadata": metadata or {},
            "user_id": user_id,
        }
        if tenant_id and settings.enable_multitenant:
            entry["tenant_id"] = tenant_id
        try:
            query = self._get_client().table("ai_memory").insert(entry)
            result = query.execute()
            return result.data[0] if result.data else entry
        except Exception as e:
            logger.warning("Supabase save_memory failed: %s", e)
            return entry

    def get_memories(
        self,
        user_id: str,
        category: str | None = None,
        limit: int = 50,
        tenant_id: Optional[str] = None,
    ) -> list[dict]:
        try:
            query = (
                self._get_client().table("ai_memory").select("*").eq("user_id", user_id)
            )
            if category:
                query = query.eq("category", category)
            query = self._build_tenant_filter(query, tenant_id)
            result = query.order("created_at", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.warning("Supabase get_memories failed: %s", e)
            return []

    def delete_memory(
        self, user_id: str, memory_id: str, tenant_id: Optional[str] = None
    ) -> bool:
        try:
            query = (
                self._get_client()
                .table("ai_memory")
                .delete()
                .eq("id", memory_id)
                .eq("user_id", user_id)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            logger.warning("Supabase delete_memory failed: %s", e)
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
    ) -> dict:
        symbol = symbol.upper()
        try:
            client = self._get_client()
            result = (
                client.table("holdings")
                .select("*")
                .eq("symbol", symbol)
                .eq("connection_id", connection_id)
                .eq("user_id", user_id)
                .execute()
            )
            if result.data:
                updated = (
                    client.table("holdings")
                    .update(
                        {
                            "name": name,
                            "type": asset_type,
                            "quantity": quantity,
                            "avg_buy_price": avg_buy_price,
                            "updated_at": "now()",
                        }
                    )
                    .eq("id", result.data[0]["id"])
                    .eq("user_id", user_id)
                    .execute()
                )
                return updated.data[0] if updated.data else result.data[0]
            else:
                holding = {
                    "id": str(uuid.uuid4()),
                    "symbol": symbol,
                    "name": name,
                    "type": asset_type,
                    "quantity": quantity,
                    "avg_buy_price": avg_buy_price,
                    "source": source,
                    "connection_id": connection_id,
                    "user_id": user_id,
                }
                inserted = client.table("holdings").insert(holding).execute()
                return inserted.data[0] if inserted.data else holding
        except Exception as e:
            logger.warning("Supabase upsert_synced_holding failed: %s", e)
            return {
                "symbol": symbol,
                "name": name,
                "type": asset_type,
                "quantity": quantity,
                "avg_buy_price": avg_buy_price,
                "source": source,
                "connection_id": connection_id,
            }

    def delete_synced_holding(
        self, user_id: str, symbol: str, connection_id: str
    ) -> bool:
        try:
            result = (
                self._get_client()
                .table("holdings")
                .delete()
                .eq("symbol", symbol.upper())
                .eq("connection_id", connection_id)
                .eq("user_id", user_id)
                .execute()
            )
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            logger.warning("Supabase delete_synced_holding failed: %s", e)
            return False

    def delete_holdings_by_connection(self, user_id: str, connection_id: str) -> int:
        try:
            result = (
                self._get_client()
                .table("holdings")
                .delete()
                .eq("connection_id", connection_id)
                .eq("user_id", user_id)
                .execute()
            )
            return len(result.data) if result.data else 0
        except Exception as e:
            logger.warning("Supabase delete_holdings_by_connection failed: %s", e)
            return 0

    def get_holdings_by_connection(
        self, user_id: str, connection_id: str
    ) -> list[dict]:
        try:
            result = (
                self._get_client()
                .table("holdings")
                .select("*")
                .eq("connection_id", connection_id)
                .eq("user_id", user_id)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.warning("Supabase get_holdings_by_connection failed: %s", e)
            return []

    # --- Connections ---

    def get_connections(
        self, user_id: str, tenant_id: Optional[str] = None
    ) -> list[dict]:
        try:
            query = (
                self._get_client()
                .table("connections")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.warning("Supabase get_connections failed: %s", e)
            return list(self._fallback_collection("connections", user_id).values())

    def get_connection(
        self, user_id: str, connection_id: str, tenant_id: Optional[str] = None
    ) -> dict | None:
        try:
            query = (
                self._get_client()
                .table("connections")
                .select("*")
                .eq("id", connection_id)
                .eq("user_id", user_id)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase get_connection failed: %s", e)
            return self._fallback_collection("connections", user_id).get(connection_id)

    def create_connection(
        self, user_id: str, data: dict, tenant_id: Optional[str] = None
    ) -> dict:
        data["user_id"] = user_id
        if tenant_id and settings.enable_multitenant:
            data["tenant_id"] = tenant_id
        try:
            result = self._get_client().table("connections").insert(data).execute()
            return result.data[0] if result.data else data
        except Exception as e:
            logger.warning("Supabase create_connection failed: %s", e)
            self._fallback_collection("connections", user_id)[data["id"]] = data
            return data

    def update_connection(
        self,
        user_id: str,
        connection_id: str,
        data: dict,
        tenant_id: Optional[str] = None,
    ) -> dict | None:
        try:
            query = (
                self._get_client()
                .table("connections")
                .update(data)
                .eq("id", connection_id)
                .eq("user_id", user_id)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase update_connection failed: %s", e)
            connection = self._fallback_collection("connections", user_id).get(connection_id)
            if not connection:
                return None
            connection.update(data)
            return connection

    def delete_connection(
        self, user_id: str, connection_id: str, tenant_id: Optional[str] = None
    ) -> bool:
        try:
            query = (
                self._get_client()
                .table("connections")
                .delete()
                .eq("id", connection_id)
                .eq("user_id", user_id)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            logger.warning("Supabase delete_connection failed: %s", e)
            return self._fallback_collection("connections", user_id).pop(connection_id, None) is not None

    def get_connections_by_provider(
        self, provider: str, tenant_id: Optional[str] = None
    ) -> list[dict]:
        try:
            query = (
                self._get_client()
                .table("connections")
                .select("*")
                .eq("provider", provider)
                .order("created_at", desc=True)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.warning("Supabase get_connections_by_provider failed: %s", e)
            rows: list[dict] = []
            for user_id, user_connections in self._workflow_fallback.get("connections", {}).items():
                for connection in user_connections.values():
                    if connection.get("provider") == provider:
                        rows.append({**connection, "user_id": user_id})
            return rows

    # --- Sync History ---

    def add_sync_history(
        self, user_id: str, data: dict, tenant_id: Optional[str] = None
    ) -> dict:
        data["user_id"] = user_id
        if tenant_id and settings.enable_multitenant:
            data["tenant_id"] = tenant_id
        try:
            result = self._get_client().table("sync_history").insert(data).execute()
            return result.data[0] if result.data else data
        except Exception as e:
            logger.warning("Supabase add_sync_history failed: %s", e)
            self._fallback_list("sync_history", user_id).insert(0, data)
            return data

    def update_sync_history(
        self,
        user_id: str,
        sync_id: str,
        data: dict,
        tenant_id: Optional[str] = None,
    ) -> dict | None:
        try:
            query = (
                self._get_client()
                .table("sync_history")
                .update(data)
                .eq("id", sync_id)
                .eq("user_id", user_id)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase update_sync_history failed: %s", e)
            for entry in self._fallback_list("sync_history", user_id):
                if entry.get("id") == sync_id:
                    entry.update(data)
                    return entry
            return None

    def get_sync_history(
        self,
        user_id: str,
        connection_id: str,
        limit: int = 20,
        tenant_id: Optional[str] = None,
    ) -> list[dict]:
        try:
            query = (
                self._get_client()
                .table("sync_history")
                .select("*")
                .eq("connection_id", connection_id)
                .eq("user_id", user_id)
                .order("started_at", desc=True)
                .limit(limit)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.warning("Supabase get_sync_history failed: %s", e)
            return [
                item
                for item in self._fallback_list("sync_history", user_id)
                if item.get("connection_id") == connection_id
            ][:limit]

    # --- RL Agent State ---

    def save_rl_agent_state(self, user_id: str, data: dict) -> dict:
        """Save RL agent state (trades, performance, settings)."""
        try:
            # Check if exists
            existing = (
                self._get_client()
                .table("rl_agent_state")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )

            if existing.data:
                # Update
                result = (
                    self._get_client()
                    .table("rl_agent_state")
                    .update(
                        {
                            "symbol": data.get("symbol"),
                            "mode": data.get("mode"),
                            "position": data.get("position"),
                            "entry_price": data.get("entry_price"),
                            "initial_balance": data.get("initial_balance"),
                            "max_position_pct": data.get("max_position_pct"),
                            "stop_loss_pct": data.get("stop_loss_pct"),
                            "take_profit_pct": data.get("take_profit_pct"),
                            "total_trades": data.get("total_trades"),
                            "updated_at": "now()",
                        }
                    )
                    .eq("user_id", user_id)
                    .execute()
                )
                return result.data[0] if result.data else data
            else:
                # Insert
                state = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "symbol": data.get("symbol", "BTC/USD"),
                    "mode": data.get("mode", "paper"),
                    "position": data.get("position", 0),
                    "entry_price": data.get("entry_price", 0),
                    "initial_balance": data.get("initial_balance", 10000),
                    "max_position_pct": data.get("max_position_pct", 0.1),
                    "stop_loss_pct": data.get("stop_loss_pct", 0.05),
                    "take_profit_pct": data.get("take_profit_pct", 0.1),
                    "total_trades": data.get("total_trades", 0),
                }
                result = (
                    self._get_client().table("rl_agent_state").insert(state).execute()
                )
                return result.data[0] if result.data else state
        except Exception as e:
            logger.warning("Supabase save_rl_agent_state failed: %s", e)
            return data

    def get_rl_agent_state(self, user_id: str) -> dict | None:
        """Get RL agent state."""
        try:
            result = (
                self._get_client()
                .table("rl_agent_state")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase get_rl_agent_state failed: %s", e)
            return None

    def save_rl_trade(self, user_id: str, trade: dict) -> dict:
        """Save a single RL trade."""
        try:
            trade_data = {
                "id": trade.get("id", str(uuid.uuid4())),
                "user_id": user_id,
                "symbol": trade.get("symbol"),
                "action": trade.get("action"),
                "price": trade.get("price"),
                "quantity": trade.get("quantity"),
                "value": trade.get("value"),
                "pnl": trade.get("pnl", 0),
                "confidence": trade.get("confidence"),
                "reason": trade.get("reason"),
                "mode": trade.get("mode"),
                "timestamp": trade.get("timestamp"),
            }
            result = self._get_client().table("rl_trades").insert(trade_data).execute()
            return result.data[0] if result.data else trade_data
        except Exception as e:
            logger.warning("Supabase save_rl_trade failed: %s", e)
            return trade

    def get_rl_trades(self, user_id: str, limit: int = 50) -> list[dict]:
        """Get RL trades history."""
        try:
            result = (
                self._get_client()
                .table("rl_trades")
                .select("*")
                .eq("user_id", user_id)
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.warning("Supabase get_rl_trades failed: %s", e)
            return []

    # --- Workflow domains ---

    def _fallback_collection(self, name: str, user_id: str):
        return self._workflow_fallback.setdefault(name, {}).setdefault(user_id, {})

    def _fallback_list(self, name: str, user_id: str):
        return self._workflow_fallback.setdefault(name, {}).setdefault(user_id, [])

    def get_inbox_items(
        self, user_id: str, tenant_id: Optional[str] = None
    ) -> list[dict]:
        try:
            query = (
                self._get_client()
                .table("inbox_items")
                .select("*")
                .eq("user_id", user_id)
                .order("priority_score", desc=True)
                .order("updated_at", desc=True)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.warning("Supabase get_inbox_items failed, using fallback: %s", e)
            return sorted(
                self._fallback_list("inbox_items", user_id),
                key=lambda item: (
                    -float(item.get("priority_score", 0.0)),
                    item.get("updated_at", ""),
                ),
            )

    def replace_inbox_items(
        self, user_id: str, items: list[dict], tenant_id: Optional[str] = None
    ) -> list[dict]:
        try:
            query = self._get_client().table("inbox_items").delete().eq("user_id", user_id)
            query = self._build_tenant_filter(query, tenant_id)
            query.execute()
            if not items:
                return []
            payload = []
            for item in items:
                row = {**item, "user_id": user_id}
                if tenant_id and settings.enable_multitenant:
                    row["tenant_id"] = tenant_id
                payload.append(row)
            result = self._get_client().table("inbox_items").insert(payload).execute()
            return result.data or payload
        except Exception as e:
            logger.warning("Supabase replace_inbox_items failed, using fallback: %s", e)
            fallback = self._fallback_list("inbox_items", user_id)
            fallback.clear()
            fallback.extend(items)
            return fallback

    def get_inbox_item(
        self, user_id: str, item_id: str, tenant_id: Optional[str] = None
    ) -> dict | None:
        try:
            query = (
                self._get_client()
                .table("inbox_items")
                .select("*")
                .eq("user_id", user_id)
                .eq("id", item_id)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data[0] if result.data else None
        except Exception:
            for item in self._fallback_list("inbox_items", user_id):
                if item.get("id") == item_id:
                    return item
            return None

    def update_inbox_item(
        self,
        user_id: str,
        item_id: str,
        data: dict,
        tenant_id: Optional[str] = None,
    ) -> dict | None:
        try:
            query = (
                self._get_client()
                .table("inbox_items")
                .update(data)
                .eq("user_id", user_id)
                .eq("id", item_id)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase update_inbox_item failed, using fallback: %s", e)
            items = self._fallback_list("inbox_items", user_id)
            for item in items:
                if item.get("id") == item_id:
                    item.update(data)
                    return item
            return None

    def get_theses(self, user_id: str, tenant_id: Optional[str] = None) -> list[dict]:
        try:
            query = (
                self._get_client()
                .table("theses")
                .select("*")
                .eq("user_id", user_id)
                .order("updated_at", desc=True)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.warning("Supabase get_theses failed, using fallback: %s", e)
            return list(self._fallback_collection("theses", user_id).values())

    def get_thesis(
        self, user_id: str, thesis_id: str, tenant_id: Optional[str] = None
    ) -> dict | None:
        try:
            query = (
                self._get_client()
                .table("theses")
                .select("*")
                .eq("user_id", user_id)
                .eq("id", thesis_id)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data[0] if result.data else None
        except Exception:
            return self._fallback_collection("theses", user_id).get(thesis_id)

    def create_thesis(
        self, user_id: str, data: dict, tenant_id: Optional[str] = None
    ) -> dict:
        thesis = {**data, "id": data.get("id", str(uuid.uuid4())), "user_id": user_id}
        if tenant_id and settings.enable_multitenant:
            thesis["tenant_id"] = tenant_id
        try:
            result = self._get_client().table("theses").insert(thesis).execute()
            return result.data[0] if result.data else thesis
        except Exception as e:
            logger.warning("Supabase create_thesis failed, using fallback: %s", e)
            self._fallback_collection("theses", user_id)[thesis["id"]] = thesis
            return thesis

    def update_thesis(
        self,
        user_id: str,
        thesis_id: str,
        data: dict,
        tenant_id: Optional[str] = None,
    ) -> dict | None:
        try:
            query = (
                self._get_client()
                .table("theses")
                .update(data)
                .eq("user_id", user_id)
                .eq("id", thesis_id)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase update_thesis failed, using fallback: %s", e)
            thesis = self._fallback_collection("theses", user_id).get(thesis_id)
            if not thesis:
                return None
            thesis.update(data)
            return thesis

    def add_thesis_event(
        self, user_id: str, thesis_id: str, data: dict, tenant_id: Optional[str] = None
    ) -> dict:
        event = {
            **data,
            "id": data.get("id", str(uuid.uuid4())),
            "thesis_id": thesis_id,
            "user_id": user_id,
        }
        if tenant_id and settings.enable_multitenant:
            event["tenant_id"] = tenant_id
        try:
            result = self._get_client().table("thesis_events").insert(event).execute()
            return result.data[0] if result.data else event
        except Exception as e:
            logger.warning("Supabase add_thesis_event failed, using fallback: %s", e)
            events = self._fallback_collection("thesis_events", user_id).setdefault(
                thesis_id, []
            )
            events.insert(0, event)
            return event

    def get_thesis_events(
        self, user_id: str, thesis_id: str, tenant_id: Optional[str] = None
    ) -> list[dict]:
        try:
            query = (
                self._get_client()
                .table("thesis_events")
                .select("*")
                .eq("user_id", user_id)
                .eq("thesis_id", thesis_id)
                .order("created_at", desc=True)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.warning("Supabase get_thesis_events failed, using fallback: %s", e)
            return self._fallback_collection("thesis_events", user_id).get(thesis_id, [])

    def get_alert_rules(
        self, user_id: str, tenant_id: Optional[str] = None
    ) -> list[dict]:
        try:
            query = (
                self._get_client()
                .table("alert_rules")
                .select("*")
                .eq("user_id", user_id)
                .order("updated_at", desc=True)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.warning("Supabase get_alert_rules failed, using fallback: %s", e)
            return list(self._fallback_collection("alert_rules", user_id).values())

    def get_alert_rule(
        self, user_id: str, rule_id: str, tenant_id: Optional[str] = None
    ) -> dict | None:
        try:
            query = (
                self._get_client()
                .table("alert_rules")
                .select("*")
                .eq("user_id", user_id)
                .eq("id", rule_id)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data[0] if result.data else None
        except Exception:
            return self._fallback_collection("alert_rules", user_id).get(rule_id)

    def create_alert_rule(
        self, user_id: str, data: dict, tenant_id: Optional[str] = None
    ) -> dict:
        rule = {**data, "id": data.get("id", str(uuid.uuid4())), "user_id": user_id}
        if tenant_id and settings.enable_multitenant:
            rule["tenant_id"] = tenant_id
        try:
            result = self._get_client().table("alert_rules").insert(rule).execute()
            return result.data[0] if result.data else rule
        except Exception as e:
            logger.warning("Supabase create_alert_rule failed, using fallback: %s", e)
            self._fallback_collection("alert_rules", user_id)[rule["id"]] = rule
            return rule

    def update_alert_rule(
        self,
        user_id: str,
        rule_id: str,
        data: dict,
        tenant_id: Optional[str] = None,
    ) -> dict | None:
        try:
            query = (
                self._get_client()
                .table("alert_rules")
                .update(data)
                .eq("user_id", user_id)
                .eq("id", rule_id)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase update_alert_rule failed, using fallback: %s", e)
            rule = self._fallback_collection("alert_rules", user_id).get(rule_id)
            if not rule:
                return None
            rule.update(data)
            return rule

    def get_research_screens(
        self, user_id: str, tenant_id: Optional[str] = None
    ) -> list[dict]:
        try:
            query = (
                self._get_client()
                .table("research_screens")
                .select("*")
                .eq("user_id", user_id)
                .order("updated_at", desc=True)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.warning("Supabase get_research_screens failed, using fallback: %s", e)
            return list(self._fallback_collection("research_screens", user_id).values())

    def save_research_screen(
        self, user_id: str, data: dict, tenant_id: Optional[str] = None
    ) -> dict:
        screen = {**data, "id": data.get("id", str(uuid.uuid4())), "user_id": user_id}
        if tenant_id and settings.enable_multitenant:
            screen["tenant_id"] = tenant_id
        try:
            result = self._get_client().table("research_screens").upsert(screen).execute()
            return result.data[0] if result.data else screen
        except Exception as e:
            logger.warning("Supabase save_research_screen failed, using fallback: %s", e)
            self._fallback_collection("research_screens", user_id)[screen["id"]] = screen
            return screen

    def get_research_snapshots(
        self, user_id: str, tenant_id: Optional[str] = None
    ) -> list[dict]:
        try:
            query = (
                self._get_client()
                .table("research_snapshots")
                .select("*")
                .eq("user_id", user_id)
                .order("captured_at", desc=True)
            )
            query = self._build_tenant_filter(query, tenant_id)
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.warning("Supabase get_research_snapshots failed, using fallback: %s", e)
            return self._fallback_list("research_snapshots", user_id)

    def save_research_snapshot(
        self, user_id: str, data: dict, tenant_id: Optional[str] = None
    ) -> dict:
        snapshot = {**data, "id": data.get("id", str(uuid.uuid4())), "user_id": user_id}
        if tenant_id and settings.enable_multitenant:
            snapshot["tenant_id"] = tenant_id
        try:
            result = (
                self._get_client().table("research_snapshots").insert(snapshot).execute()
            )
            return result.data[0] if result.data else snapshot
        except Exception as e:
            logger.warning("Supabase save_research_snapshot failed, using fallback: %s", e)
            self._fallback_list("research_snapshots", user_id).insert(0, snapshot)
            return snapshot
