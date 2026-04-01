"""Per-user MyInvestIA Telegram bot orchestration."""

from __future__ import annotations

import asyncio
import hashlib
import html
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from app.services.alert_scorer import scan_symbols
from app.services.inbox_service import build_briefing_from_inbox
from app.services.store import store
from app.services.telegram_service import telegram_service
from app.services.thesis_service import list_theses

logger = logging.getLogger(__name__)

BOT_CONNECTION_ID = "myinvestia-personal-bot"
BOT_PROVIDER = "telegram_personal_bot"
BOT_LABEL = "MyInvestIA Personal Bot"
BOT_CONNECT_TTL_MINUTES = 30
SCHEDULER_POLL_SECONDS = 60

DEFAULT_SCAN_SYMBOLS = [
    {"symbol": "SPY", "type": "etf"},
    {"symbol": "QQQ", "type": "etf"},
    {"symbol": "AAPL", "type": "stock"},
    {"symbol": "MSFT", "type": "stock"},
]

SEVERITY_RANK = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _escape(value: object) -> str:
    return html.escape(str(value))


def _default_metadata() -> dict:
    return {
        "enabled": False,
        "connected": False,
        "cadence_minutes": 30,
        "min_severity": "high",
        "include_briefing": True,
        "include_inbox": True,
        "include_portfolio": True,
        "include_watchlist": True,
        "include_macro": True,
        "include_news": True,
        "include_theses": True,
        "include_buy_sell": True,
        "send_only_on_changes": True,
        "provisioned_defaults": False,
        "pending_code": None,
        "pending_expires_at": None,
        "bot_name": None,
        "bot_username": None,
        "chat_id": None,
        "chat_name": None,
        "telegram_user_id": None,
        "telegram_username": None,
        "verified_at": None,
        "last_run_at": None,
        "last_delivery_at": None,
        "last_digest_hash": None,
        "last_test_at": None,
        "last_error": None,
        "last_reason": None,
        "last_message_count": 0,
        "last_alert_count": 0,
    }


def _status_from_metadata(metadata: dict) -> str:
    if metadata.get("connected"):
        return "active" if metadata.get("enabled") else "disconnected"
    if metadata.get("pending_code"):
        return "pending"
    return "disconnected"


def _build_connect_url(bot_username: str | None, code: str | None) -> str | None:
    if not bot_username or not code:
        return None
    return f"https://t.me/{bot_username}?start={code}"


def _matches_start_code(text: str, code: str) -> bool:
    normalized = text.strip()
    if normalized == code:
        return True
    if normalized.startswith("/start"):
        parts = normalized.split(maxsplit=1)
        return len(parts) == 2 and parts[1].strip() == code
    return False


class PersonalBotService:
    """Manage personal Telegram bot connection, delivery, and scheduling."""

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None

    def _store_call(self, method_name: str, *args, tenant_id: str | None = None):
        method = getattr(store, method_name)
        if tenant_id is None:
            return method(*args)
        return method(*args, tenant_id=tenant_id)

    def _get_connection(self, user_id: str, tenant_id: str | None = None) -> dict | None:
        return self._store_call("get_connection", user_id, BOT_CONNECTION_ID, tenant_id=tenant_id)

    def _get_metadata(self, user_id: str, tenant_id: str | None = None) -> dict:
        connection = self._get_connection(user_id, tenant_id)
        metadata = dict(_default_metadata())
        if connection:
            metadata.update(connection.get("metadata") or {})
        if connection and connection.get("status") == "active" and metadata.get("chat_id"):
            metadata["connected"] = True
        return metadata

    def get_connected_chat_id(
        self, user_id: str, tenant_id: str | None = None
    ) -> str | None:
        metadata = self._get_metadata(user_id, tenant_id)
        if metadata.get("connected") and metadata.get("chat_id"):
            return str(metadata.get("chat_id"))
        return None

    def _upsert_connection(
        self,
        user_id: str,
        metadata: dict,
        tenant_id: str | None = None,
    ) -> dict:
        now = _iso_now()
        status = _status_from_metadata(metadata)
        payload = {
            "id": BOT_CONNECTION_ID,
            "type": "broker",
            "provider": BOT_PROVIDER,
            "label": BOT_LABEL,
            "status": status,
            "last_sync_at": metadata.get("last_delivery_at") or metadata.get("last_run_at"),
            "last_sync_status": "success" if not metadata.get("last_error") else "failed",
            "last_sync_error": metadata.get("last_error"),
            "sync_count": int(metadata.get("sync_count", 0)),
            "created_at": now,
            "metadata": metadata,
            "wallet_address": None,
            "chain": None,
            "credentials_encrypted": None,
        }
        existing = self._get_connection(user_id, tenant_id)
        if existing:
            payload["created_at"] = existing.get("created_at") or now
            return self._store_call(
                "update_connection",
                user_id,
                BOT_CONNECTION_ID,
                payload,
                tenant_id=tenant_id,
            ) or {**existing, **payload}
        return self._store_call("create_connection", user_id, payload, tenant_id=tenant_id)

    def _gather_symbol_groups(
        self, user_id: str, tenant_id: str | None = None
    ) -> tuple[list[dict], list[dict]]:
        holdings_symbols: list[dict] = []
        watchlist_symbols: list[dict] = []
        seen_holdings: set[str] = set()
        seen_watchlist: set[str] = set()

        for holding in self._store_call("get_holdings", user_id, tenant_id=tenant_id):
            symbol = str(holding.get("symbol", "")).upper()
            if symbol and symbol not in seen_holdings:
                holdings_symbols.append(
                    {"symbol": symbol, "type": holding.get("type", "stock")}
                )
                seen_holdings.add(symbol)

        for watchlist in self._store_call("get_watchlists", user_id, tenant_id=tenant_id):
            for asset in watchlist.get("assets", []):
                symbol = str(asset.get("symbol", "")).upper()
                if symbol and symbol not in seen_watchlist and symbol not in seen_holdings:
                    watchlist_symbols.append(
                        {"symbol": symbol, "type": asset.get("type", "stock")}
                    )
                    seen_watchlist.add(symbol)

        return holdings_symbols, watchlist_symbols

    def _get_status_payload(
        self, user_id: str, tenant_id: str | None = None, *, include_history: bool = True
    ) -> dict:
        metadata = self._get_metadata(user_id, tenant_id)
        bot_info = {
            "bot_name": metadata.get("bot_name"),
            "bot_username": metadata.get("bot_username"),
        }
        connect_url = _build_connect_url(
            bot_info["bot_username"],
            metadata.get("pending_code"),
        )
        history = []
        if include_history:
            history = self._store_call(
                "get_sync_history",
                user_id,
                BOT_CONNECTION_ID,
                10,
                tenant_id=tenant_id,
            )

        return {
            "available": telegram_service.bot_available,
            "enabled": bool(metadata.get("enabled")),
            "connected": bool(metadata.get("connected") and metadata.get("chat_id")),
            "status": _status_from_metadata(metadata),
            "bot_name": bot_info["bot_name"],
            "bot_username": bot_info["bot_username"],
            "chat_id": metadata.get("chat_id"),
            "chat_name": metadata.get("chat_name"),
            "telegram_username": metadata.get("telegram_username"),
            "cadence_minutes": int(metadata.get("cadence_minutes", 30)),
            "min_severity": metadata.get("min_severity", "high"),
            "include_briefing": bool(metadata.get("include_briefing")),
            "include_inbox": bool(metadata.get("include_inbox")),
            "include_portfolio": bool(metadata.get("include_portfolio")),
            "include_watchlist": bool(metadata.get("include_watchlist")),
            "include_macro": bool(metadata.get("include_macro")),
            "include_news": bool(metadata.get("include_news")),
            "include_theses": bool(metadata.get("include_theses")),
            "include_buy_sell": bool(metadata.get("include_buy_sell")),
            "send_only_on_changes": bool(metadata.get("send_only_on_changes", True)),
            "provisioned_defaults": bool(metadata.get("provisioned_defaults")),
            "pending_code": metadata.get("pending_code"),
            "pending_expires_at": metadata.get("pending_expires_at"),
            "connect_url": connect_url,
            "verified_at": metadata.get("verified_at"),
            "last_run_at": metadata.get("last_run_at"),
            "last_delivery_at": metadata.get("last_delivery_at"),
            "last_test_at": metadata.get("last_test_at"),
            "last_error": metadata.get("last_error"),
            "last_reason": metadata.get("last_reason"),
            "last_message_count": int(metadata.get("last_message_count", 0)),
            "last_alert_count": int(metadata.get("last_alert_count", 0)),
            "history": history,
        }

    async def get_status(self, user_id: str, tenant_id: str | None = None) -> dict:
        metadata = self._get_metadata(user_id, tenant_id)
        if telegram_service.bot_available and (
            not metadata.get("bot_username") or not metadata.get("bot_name")
        ):
            bot_info = await telegram_service.get_bot_info()
            if bot_info:
                metadata["bot_name"] = bot_info.get("first_name")
                metadata["bot_username"] = bot_info.get("username")
                self._upsert_connection(user_id, metadata, tenant_id)
        return self._get_status_payload(user_id, tenant_id)

    async def start_connect(self, user_id: str, tenant_id: str | None = None) -> dict:
        if not telegram_service.bot_available:
            raise ValueError("Telegram bot no configurado en el servidor")

        metadata = self._get_metadata(user_id, tenant_id)
        bot_info = await telegram_service.get_bot_info()
        if not bot_info:
            raise ValueError("No se pudo cargar la informacion del bot de Telegram")

        code = secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:12]
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=BOT_CONNECT_TTL_MINUTES)).isoformat()
        metadata.update(
            {
                "pending_code": code,
                "pending_expires_at": expires_at,
                "bot_name": bot_info.get("first_name"),
                "bot_username": bot_info.get("username"),
                "last_error": None,
                "connected": False,
            }
        )
        self._upsert_connection(user_id, metadata, tenant_id)
        return self._get_status_payload(user_id, tenant_id)

    async def verify_connect(self, user_id: str, tenant_id: str | None = None) -> dict:
        metadata = self._get_metadata(user_id, tenant_id)
        code = metadata.get("pending_code")
        expires_at = _parse_dt(metadata.get("pending_expires_at"))
        if not code:
            raise ValueError("No hay una conexion pendiente para verificar")
        if expires_at and expires_at < datetime.now(timezone.utc):
            raise ValueError("El codigo de conexion ha caducado")

        updates = await telegram_service.get_updates(limit=100)
        for update in reversed(updates):
            message = update.get("message") or update.get("edited_message") or {}
            text = str(message.get("text") or "").strip()
            if not _matches_start_code(text, code):
                continue
            chat = message.get("chat") or {}
            from_user = message.get("from") or {}
            chat_id = str(chat.get("id") or "")
            if not chat_id:
                continue
            metadata.update(
                {
                    "connected": True,
                    "enabled": True,
                    "pending_code": None,
                    "pending_expires_at": None,
                    "chat_id": chat_id,
                    "chat_name": chat.get("title")
                    or from_user.get("first_name")
                    or from_user.get("username")
                    or "Telegram",
                    "telegram_user_id": str(from_user.get("id") or ""),
                    "telegram_username": from_user.get("username"),
                    "verified_at": _iso_now(),
                    "last_error": None,
                }
            )
            self._upsert_connection(user_id, metadata, tenant_id)
            await telegram_service.send_message_to_chat(
                chat_id,
                "✅ <b>MyInvestIA conectado</b>\n\n"
                "A partir de ahora te puedo enviar alertas, resumenes y señales de tus activos.",
            )
            return self._get_status_payload(user_id, tenant_id)

        raise ValueError(
            "No he encontrado el /start del bot todavia. Abre el enlace, pulsa Start y vuelve a verificar."
        )

    async def disconnect(self, user_id: str, tenant_id: str | None = None) -> dict:
        metadata = self._get_metadata(user_id, tenant_id)
        metadata.update(
            {
                "enabled": False,
                "connected": False,
                "pending_code": None,
                "pending_expires_at": None,
                "chat_id": None,
                "chat_name": None,
                "telegram_user_id": None,
                "telegram_username": None,
                "last_error": None,
            }
        )
        self._upsert_connection(user_id, metadata, tenant_id)
        return self._get_status_payload(user_id, tenant_id)

    async def update_config(
        self,
        user_id: str,
        updates: dict,
        tenant_id: str | None = None,
    ) -> dict:
        metadata = self._get_metadata(user_id, tenant_id)
        allowed_fields = {
            "enabled",
            "cadence_minutes",
            "min_severity",
            "include_briefing",
            "include_inbox",
            "include_portfolio",
            "include_watchlist",
            "include_macro",
            "include_news",
            "include_theses",
            "include_buy_sell",
            "send_only_on_changes",
        }
        for key, value in updates.items():
            if key in allowed_fields and value is not None:
                metadata[key] = value
        if not metadata.get("connected"):
            metadata["enabled"] = False
        self._upsert_connection(user_id, metadata, tenant_id)
        return self._get_status_payload(user_id, tenant_id)

    async def send_test(self, user_id: str, tenant_id: str | None = None) -> dict:
        metadata = self._get_metadata(user_id, tenant_id)
        chat_id = metadata.get("chat_id")
        if not chat_id:
            raise ValueError("Bot no conectado todavia")
        result = await telegram_service.send_message_to_chat(
            chat_id,
            "🧪 <b>Test MyInvestIA</b>\n\n"
            "Tu bot personal esta listo. Recibiras alertas de cartera, inbox, tesis y eventos.",
        )
        metadata["last_test_at"] = _iso_now()
        metadata["last_error"] = None if result else "No se pudo enviar el test"
        self._upsert_connection(user_id, metadata, tenant_id)
        return {
            "success": result is not None,
            "message": "Test enviado" if result else "No se pudo enviar el test",
            "status": self._get_status_payload(user_id, tenant_id),
        }

    async def provision_default_rules(
        self, user_id: str, tenant_id: str | None = None
    ) -> dict:
        holdings_symbols, watchlist_symbols = self._gather_symbol_groups(user_id, tenant_id)
        holdings = [item["symbol"] for item in holdings_symbols]
        watchlist = [item["symbol"] for item in watchlist_symbols]
        universe = holdings or watchlist or [item["symbol"] for item in DEFAULT_SCAN_SYMBOLS]

        existing_rules = self._store_call("get_alert_rules", user_id, tenant_id=tenant_id)
        existing_names = {rule.get("name") for rule in existing_rules}
        created = 0
        now = _iso_now()
        templates = [
            {
                "name": "Personal Bot | Riesgo cartera",
                "symbols": holdings or universe,
                "conditions": [
                    {"field": "severity", "operator": "contains", "value": "high", "source": "alerts_engine"},
                    {"field": "suggested_action", "operator": "contains", "value": "sell", "source": "alerts_engine"},
                ],
                "cooldown_minutes": 120,
                "delivery_channels": ["telegram"],
                "linked_thesis_id": None,
                "active": True,
            },
            {
                "name": "Personal Bot | Oportunidades watchlist",
                "symbols": watchlist or universe,
                "conditions": [
                    {"field": "suggested_action", "operator": "contains", "value": "buy", "source": "alerts_engine"},
                    {"field": "confidence", "operator": "gte", "value": "0.65", "source": "alerts_engine"},
                ],
                "cooldown_minutes": 180,
                "delivery_channels": ["telegram"],
                "linked_thesis_id": None,
                "active": True,
            },
            {
                "name": "Personal Bot | Catalizadores y filings",
                "symbols": universe,
                "conditions": [
                    {"field": "event_type", "operator": "contains", "value": "earnings", "source": "event_engine"},
                    {"field": "event_type", "operator": "contains", "value": "filing", "source": "event_engine"},
                ],
                "cooldown_minutes": 240,
                "delivery_channels": ["telegram"],
                "linked_thesis_id": None,
                "active": True,
            },
        ]

        for template in templates:
            if template["name"] in existing_names:
                continue
            self._store_call(
                "create_alert_rule",
                user_id,
                {
                    **template,
                    "created_at": now,
                    "updated_at": now,
                },
                tenant_id=tenant_id,
            )
            created += 1

        metadata = self._get_metadata(user_id, tenant_id)
        metadata["provisioned_defaults"] = True
        self._upsert_connection(user_id, metadata, tenant_id)
        return {
            "success": True,
            "created_rules": created,
            "message": f"{created} reglas creadas" if created else "Las reglas por defecto ya existian",
            "status": self._get_status_payload(user_id, tenant_id),
        }

    def get_history(
        self, user_id: str, tenant_id: str | None = None, limit: int = 20
    ) -> list[dict]:
        return self._store_call(
            "get_sync_history",
            user_id,
            BOT_CONNECTION_ID,
            limit,
            tenant_id=tenant_id,
        )

    def _alerts_to_rows(self, alerts: list) -> list[dict]:
        rows = []
        for alert in alerts:
            rows.append(
                {
                    "id": getattr(alert, "id", str(uuid.uuid4())),
                    "title": getattr(alert, "title", "Alert"),
                    "description": getattr(alert, "description", ""),
                    "severity": getattr(getattr(alert, "severity", None), "value", "medium"),
                    "asset_symbol": getattr(alert, "asset_symbol", None),
                    "suggested_action": getattr(getattr(alert, "suggested_action", None), "value", "monitor"),
                    "confidence": float(getattr(alert, "confidence", 0.0)),
                    "reasoning": getattr(alert, "reasoning", ""),
                    "created_at": getattr(alert, "created_at", _iso_now()),
                }
            )
        return rows

    def _meets_threshold(self, severity: str, threshold: str) -> bool:
        return SEVERITY_RANK.get(severity, 0) >= SEVERITY_RANK.get(threshold, 2)

    def _build_digest_hash(
        self,
        top_items: list[dict],
        alerts: list[dict],
        at_risk_theses: list[dict],
        events: list[dict],
    ) -> str:
        parts = [
            *(item.get("id", "") for item in top_items[:5]),
            *(alert.get("id", "") for alert in alerts[:6]),
            *(
                f"{thesis.get('id', '')}:{thesis.get('review_state', '')}"
                for thesis in at_risk_theses[:4]
            ),
            *(event.get("id", "") for event in events[:4]),
        ]
        raw = "|".join(parts)
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def _build_summary_message(
        self,
        *,
        holdings_count: int,
        watchlist_count: int,
        top_items: list[dict],
        events: list[dict],
        include_macro: bool,
    ) -> str:
        lines = [
            "🧠 <b>MyInvestIA Personal Bot</b>",
            f"Cartera: <b>{holdings_count}</b> activos | Watchlist: <b>{watchlist_count}</b>",
        ]
        if top_items:
            lines.append("")
            lines.append("<b>Prioridades ahora</b>")
            for item in top_items[:3]:
                symbol = item.get("primary_symbol") or ", ".join(item.get("symbols", [])[:2])
                lines.append(
                    f"• <b>{_escape(symbol or item.get('scope', 'mercado'))}</b> — {_escape(item.get('title', 'Insight'))}"
                )
                lines.append(f"  {_escape(item.get('why_now') or item.get('summary') or '')}")
        if include_macro and events:
            lines.append("")
            lines.append("<b>Proximos catalizadores</b>")
            for event in events[:3]:
                symbol = event.get("symbol")
                prefix = f"{symbol} " if symbol else ""
                lines.append(f"• {_escape(prefix + event.get('title', 'Evento'))}")
        return "\n".join(lines)

    def _build_alerts_message(self, alerts: list[dict]) -> str:
        lines = ["🚨 <b>Señales para vigilar o actuar</b>"]
        for alert in alerts[:5]:
            action = str(alert.get("suggested_action", "monitor")).upper()
            confidence = float(alert.get("confidence", 0.0))
            symbol = alert.get("asset_symbol") or "MERCADO"
            lines.append(
                f"• <b>{_escape(symbol)}</b> — {_escape(alert.get('title', 'Alert'))}"
            )
            lines.append(
                f"  {action} | {_escape(alert.get('severity', 'medium'))} | confianza {confidence:.0%}"
            )
        return "\n".join(lines)

    def _build_thesis_message(self, theses: list[dict]) -> str:
        lines = ["📌 <b>Tesis en riesgo</b>"]
        for thesis in theses[:4]:
            lines.append(
                f"• <b>{_escape(thesis.get('symbol', 'N/A'))}</b> — "
                f"{_escape(thesis.get('review_state', 'validating'))}"
            )
            if thesis.get("invalidation"):
                lines.append(f"  Invalidacion: {_escape(thesis['invalidation'])}")
        return "\n".join(lines)

    async def _deliver(
        self,
        user_id: str,
        tenant_id: str | None = None,
        *,
        reason: str,
        force: bool,
    ) -> dict:
        metadata = self._get_metadata(user_id, tenant_id)
        chat_id = metadata.get("chat_id")
        if not chat_id:
            raise ValueError("Bot no conectado")

        holdings_symbols, watchlist_symbols = self._gather_symbol_groups(user_id, tenant_id)
        symbols_to_scan: list[dict] = []
        if metadata.get("include_portfolio"):
            symbols_to_scan.extend(holdings_symbols)
        if metadata.get("include_watchlist"):
            for item in watchlist_symbols:
                if item["symbol"] not in {entry["symbol"] for entry in symbols_to_scan}:
                    symbols_to_scan.append(item)
        if not symbols_to_scan and metadata.get("include_buy_sell"):
            symbols_to_scan = list(DEFAULT_SCAN_SYMBOLS)

        briefing = await build_briefing_from_inbox(user_id, tenant_id, preset="premarket")
        top_items = briefing.get("top_inbox_items", []) if metadata.get("include_inbox") else []
        events = briefing.get("next_events", []) if metadata.get("include_macro") else []

        raw_alerts = await scan_symbols(symbols_to_scan) if symbols_to_scan else []
        alerts = self._alerts_to_rows(raw_alerts)
        notify_alerts = [
            alert
            for alert in alerts
            if self._meets_threshold(alert.get("severity", "medium"), metadata.get("min_severity", "high"))
        ]

        at_risk_theses = []
        if metadata.get("include_theses"):
            theses = list_theses(user_id, tenant_id)
            at_risk_theses = [
                thesis
                for thesis in theses
                if thesis.get("review_state") in {"at_risk", "broken"}
            ][:4]

        digest_hash = self._build_digest_hash(top_items, notify_alerts, at_risk_theses, events)
        last_digest_hash = metadata.get("last_digest_hash")
        if (
            not force
            and metadata.get("send_only_on_changes", True)
            and digest_hash
            and digest_hash == last_digest_hash
        ):
            now = _iso_now()
            metadata.update(
                {
                    "last_run_at": now,
                    "last_reason": f"{reason}:skipped",
                    "last_error": None,
                    "last_message_count": 0,
                    "last_alert_count": len(notify_alerts),
                }
            )
            self._upsert_connection(user_id, metadata, tenant_id)
            record = {
                "id": str(uuid.uuid4()),
                "connection_id": BOT_CONNECTION_ID,
                "started_at": now,
                "completed_at": now,
                "status": "skipped",
                "reason": reason,
                "summary": "Sin cambios materiales desde el ultimo envio",
                "message_count": 0,
                "alert_count": len(notify_alerts),
                "fingerprint": digest_hash,
            }
            self._store_call("add_sync_history", user_id, record, tenant_id=tenant_id)
            return {
                "success": True,
                "message": "Sin cambios relevantes; no se ha enviado nada",
                "sent_messages": 0,
                "sent_alerts": 0,
                "alerts_generated": len(alerts),
                "top_items": len(top_items),
                "events": len(events),
                "thesis_watch": len(at_risk_theses),
                "skipped": True,
            }

        messages: list[str] = []
        messages.append(
            self._build_summary_message(
                holdings_count=len(holdings_symbols),
                watchlist_count=len(watchlist_symbols),
                top_items=top_items,
                events=events,
                include_macro=bool(metadata.get("include_macro")),
            )
        )
        if metadata.get("include_buy_sell") and notify_alerts:
            messages.append(self._build_alerts_message(notify_alerts))
        if at_risk_theses:
            messages.append(self._build_thesis_message(at_risk_theses))

        sent_messages = 0
        for message in messages:
            result = await telegram_service.send_message_to_chat(chat_id, message)
            if result is not None:
                sent_messages += 1

        now = _iso_now()
        metadata.update(
            {
                "last_run_at": now,
                "last_delivery_at": now if sent_messages else metadata.get("last_delivery_at"),
                "last_digest_hash": digest_hash,
                "last_error": None if sent_messages else "No se pudo enviar el digest",
                "last_reason": reason,
                "last_message_count": sent_messages,
                "last_alert_count": len(notify_alerts),
                "sync_count": int(metadata.get("sync_count", 0)) + (1 if sent_messages else 0),
            }
        )
        self._upsert_connection(user_id, metadata, tenant_id)
        record = {
            "id": str(uuid.uuid4()),
            "connection_id": BOT_CONNECTION_ID,
            "started_at": now,
            "completed_at": now,
            "status": "success" if sent_messages else "failed",
            "reason": reason,
            "summary": f"{sent_messages} mensajes, {len(notify_alerts)} alertas relevantes",
            "message_count": sent_messages,
            "alert_count": len(notify_alerts),
            "fingerprint": digest_hash,
        }
        self._store_call("add_sync_history", user_id, record, tenant_id=tenant_id)
        return {
            "success": sent_messages > 0,
            "message": "Bot ejecutado" if sent_messages else "No se pudo enviar el digest",
            "sent_messages": sent_messages,
            "sent_alerts": len(notify_alerts),
            "alerts_generated": len(alerts),
            "top_items": len(top_items),
            "events": len(events),
            "thesis_watch": len(at_risk_theses),
            "skipped": False,
        }

    async def run_now(self, user_id: str, tenant_id: str | None = None) -> dict:
        return await self._deliver(user_id, tenant_id, reason="manual", force=True)

    async def run_due_bots(self) -> None:
        if not telegram_service.bot_available:
            return
        connections = self._store_call("get_connections_by_provider", BOT_PROVIDER)
        now = datetime.now(timezone.utc)
        for connection in connections:
            user_id = connection.get("user_id")
            if not user_id:
                continue
            metadata = dict(_default_metadata())
            metadata.update(connection.get("metadata") or {})
            if not metadata.get("enabled") or not metadata.get("connected") or not metadata.get("chat_id"):
                continue
            last_run = _parse_dt(metadata.get("last_run_at"))
            cadence = max(int(metadata.get("cadence_minutes", 30)), 5)
            if last_run and now < last_run + timedelta(minutes=cadence):
                continue
            try:
                await self._deliver(
                    user_id,
                    connection.get("tenant_id"),
                    reason="scheduled",
                    force=False,
                )
            except Exception as e:
                logger.warning("Personal bot scheduled run failed for %s: %s", user_id, e)
                metadata["last_error"] = str(e)
                self._upsert_connection(user_id, metadata, connection.get("tenant_id"))

    async def _scheduler_loop(self):
        while self._running:
            try:
                await self.run_due_bots()
            except Exception as e:
                logger.warning("Personal bot scheduler iteration failed: %s", e)
            await asyncio.sleep(SCHEDULER_POLL_SECONDS)

    def start_scheduler(self):
        if self._running or not telegram_service.bot_available:
            return
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Personal bot scheduler started")

    async def stop_scheduler(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None


personal_bot_service = PersonalBotService()
