"""Supabase-backed data store for portfolio, watchlists, and AI memory.

Multi-user: all operations require a user_id parameter to scope data.
The backend uses the service_role key (bypasses RLS) so we must filter
by user_id explicitly in every query.
"""

import logging
import uuid

from app.config import settings

logger = logging.getLogger(__name__)


class SupabaseStore:
    """Supabase-backed store — all methods require user_id."""

    def __init__(self):
        self._client = None

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

    # --- Portfolio ---

    def get_holdings(self, user_id: str) -> list[dict]:
        try:
            result = (
                self._get_client()
                .table("holdings")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            holdings = result.data or []
            for h in holdings:
                h.setdefault("source", "manual")
                h.setdefault("connection_id", None)
            return holdings
        except Exception as e:
            logger.warning("Supabase get_holdings failed: %s", e)
            return []

    def get_holding(self, user_id: str, symbol: str) -> dict | None:
        try:
            result = (
                self._get_client()
                .table("holdings")
                .select("*")
                .eq("user_id", user_id)
                .eq("symbol", symbol.upper())
                .execute()
            )
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
    ) -> dict:
        symbol = symbol.upper()
        existing = self.get_holding(user_id, symbol)
        client = self._get_client()

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

        holding = {
            "symbol": symbol,
            "name": name,
            "type": asset_type,
            "quantity": quantity,
            "avg_buy_price": avg_buy_price,
            "user_id": user_id,
        }
        result = client.table("holdings").insert(holding).execute()
        return result.data[0] if result.data else holding

    def update_holding(
        self,
        user_id: str,
        symbol: str,
        quantity: float | None = None,
        avg_buy_price: float | None = None,
    ) -> dict | None:
        symbol = symbol.upper()
        existing = self.get_holding(user_id, symbol)
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

    def delete_holding(self, user_id: str, symbol: str) -> bool:
        symbol = symbol.upper()
        try:
            result = (
                self._get_client()
                .table("holdings")
                .delete()
                .eq("user_id", user_id)
                .eq("symbol", symbol)
                .execute()
            )
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            logger.warning("Supabase delete_holding failed for %s: %s", symbol, e)
            return False

    # --- Watchlists ---

    def get_watchlists(self, user_id: str) -> list[dict]:
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
        self, user_id: str, category: str, content: str, metadata: dict | None = None
    ) -> dict:
        entry = {
            "id": str(uuid.uuid4()),
            "category": category,
            "content": content,
            "metadata": metadata or {},
            "user_id": user_id,
        }
        try:
            result = self._get_client().table("ai_memory").insert(entry).execute()
            return result.data[0] if result.data else entry
        except Exception as e:
            logger.warning("Supabase save_memory failed: %s", e)
            return entry

    def get_memories(
        self, user_id: str, category: str | None = None, limit: int = 50
    ) -> list[dict]:
        try:
            query = (
                self._get_client().table("ai_memory").select("*").eq("user_id", user_id)
            )
            if category:
                query = query.eq("category", category)
            result = query.order("created_at", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.warning("Supabase get_memories failed: %s", e)
            return []

    def delete_memory(self, user_id: str, memory_id: str) -> bool:
        try:
            result = (
                self._get_client()
                .table("ai_memory")
                .delete()
                .eq("id", memory_id)
                .eq("user_id", user_id)
                .execute()
            )
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

    def get_connections(self, user_id: str) -> list[dict]:
        try:
            result = (
                self._get_client()
                .table("connections")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.warning("Supabase get_connections failed: %s", e)
            return []

    def get_connection(self, user_id: str, connection_id: str) -> dict | None:
        try:
            result = (
                self._get_client()
                .table("connections")
                .select("*")
                .eq("id", connection_id)
                .eq("user_id", user_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase get_connection failed: %s", e)
            return None

    def create_connection(self, user_id: str, data: dict) -> dict:
        data["user_id"] = user_id
        try:
            result = self._get_client().table("connections").insert(data).execute()
            return result.data[0] if result.data else data
        except Exception as e:
            logger.warning("Supabase create_connection failed: %s", e)
            return data

    def update_connection(
        self, user_id: str, connection_id: str, data: dict
    ) -> dict | None:
        try:
            result = (
                self._get_client()
                .table("connections")
                .update(data)
                .eq("id", connection_id)
                .eq("user_id", user_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase update_connection failed: %s", e)
            return None

    def delete_connection(self, user_id: str, connection_id: str) -> bool:
        try:
            result = (
                self._get_client()
                .table("connections")
                .delete()
                .eq("id", connection_id)
                .eq("user_id", user_id)
                .execute()
            )
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            logger.warning("Supabase delete_connection failed: %s", e)
            return False

    # --- Sync History ---

    def add_sync_history(self, user_id: str, data: dict) -> dict:
        data["user_id"] = user_id
        try:
            result = self._get_client().table("sync_history").insert(data).execute()
            return result.data[0] if result.data else data
        except Exception as e:
            logger.warning("Supabase add_sync_history failed: %s", e)
            return data

    def update_sync_history(
        self, user_id: str, sync_id: str, data: dict
    ) -> dict | None:
        try:
            result = (
                self._get_client()
                .table("sync_history")
                .update(data)
                .eq("id", sync_id)
                .eq("user_id", user_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase update_sync_history failed: %s", e)
            return None

    def get_sync_history(
        self, user_id: str, connection_id: str, limit: int = 20
    ) -> list[dict]:
        try:
            result = (
                self._get_client()
                .table("sync_history")
                .select("*")
                .eq("connection_id", connection_id)
                .eq("user_id", user_id)
                .order("started_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.warning("Supabase get_sync_history failed: %s", e)
            return []

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
