"""Journal and decision log service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from app.services.market_data import market_data_service
from app.services.store import store


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


JournalEntryType = Literal["decision", "reflection", "lesson", "observation", "review"]


def list_journal_entries(
    user_id: str,
    tenant_id: str | None = None,
    limit: int = 50,
    entry_type: JournalEntryType | None = None,
) -> list[dict]:
    entries = store.get_journal_entries(user_id, tenant_id, limit=limit * 2)
    if entry_type:
        entries = [e for e in entries if e.get("entry_type") == entry_type]
    return sorted(entries, key=lambda e: e.get("created_at", ""), reverse=True)[:limit]


def get_journal_entry(
    user_id: str,
    entry_id: str,
    tenant_id: str | None = None,
) -> dict | None:
    return store.get_journal_entry(user_id, entry_id, tenant_id)


def create_journal_entry(
    user_id: str,
    data: dict,
    tenant_id: str | None = None,
) -> dict:
    now = _iso_now()
    entry = store.create_journal_entry(
        user_id,
        {
            "entry_type": data.get("entry_type", "observation"),
            "title": data.get("title", ""),
            "content": data.get("content", ""),
            "symbol": data.get("symbol"),
            "thesis_id": data.get("thesis_id"),
            "tags": data.get("tags", []),
            "mood": data.get("mood"),
            "outcome": data.get("outcome"),
            "created_at": now,
            "updated_at": now,
        },
        tenant_id,
    )
    return entry


def update_journal_entry(
    user_id: str,
    entry_id: str,
    data: dict,
    tenant_id: str | None = None,
) -> dict | None:
    updates = {k: v for k, v in data.items() if v is not None}
    if not updates:
        return store.get_journal_entry(user_id, entry_id, tenant_id)
    updates["updated_at"] = _iso_now()
    return store.update_journal_entry(user_id, entry_id, updates, tenant_id)


def delete_journal_entry(
    user_id: str,
    entry_id: str,
    tenant_id: str | None = None,
) -> bool:
    return store.delete_journal_entry(user_id, entry_id, tenant_id)


async def create_decision_from_thesis(
    user_id: str,
    thesis_id: str,
    decision: Literal["buy", "sell", "hold"],
    reason: str,
    tenant_id: str | None = None,
) -> dict:
    thesis = store.get_thesis(user_id, thesis_id, tenant_id)
    if not thesis:
        raise ValueError("Thesis not found")

    symbol = thesis.get("symbol", "")
    quote = None
    if symbol:
        try:
            quote = await market_data_service.get_quote(symbol)
        except Exception:
            pass

    entry = store.create_journal_entry(
        user_id,
        {
            "entry_type": "decision",
            "title": f"Decisión: {decision.upper()} {symbol}",
            "content": reason,
            "symbol": symbol,
            "thesis_id": thesis_id,
            "tags": [
                decision,
                thesis.get("stance", "base"),
                thesis.get("horizon", "medium"),
            ],
            "outcome": {
                "decision": decision,
                "thesis_id": thesis_id,
                "price_at_decision": quote.get("price") if quote else None,
                "conviction_at_decision": thesis.get("conviction"),
            },
            "created_at": _iso_now(),
            "updated_at": _iso_now(),
        },
        tenant_id,
    )
    return entry


async def record_outcome(
    user_id: str,
    entry_id: str,
    result: Literal["success", "failure", "neutral"],
    notes: str,
    tenant_id: str | None = None,
) -> dict | None:
    entry = store.get_journal_entry(user_id, entry_id, tenant_id)
    if not entry:
        return None

    outcome_data = {
        "result": result,
        "notes": notes,
        "recorded_at": _iso_now(),
    }

    if entry.get("outcome"):
        outcome_data["previous_outcome"] = entry["outcome"]

    return store.update_journal_entry(
        user_id,
        entry_id,
        {"outcome": outcome_data, "updated_at": _iso_now()},
        tenant_id,
    )


def get_journal_stats(user_id: str, tenant_id: str | None = None) -> dict:
    entries = store.get_journal_entries(user_id, tenant_id, limit=500)

    by_type: dict[str, int] = {}
    by_symbol: dict[str, int] = {}
    decisions = [e for e in entries if e.get("entry_type") == "decision"]

    for entry in entries:
        entry_type = entry.get("entry_type", "unknown")
        by_type[entry_type] = by_type.get(entry_type, 0) + 1

        symbol = entry.get("symbol")
        if symbol:
            by_symbol[symbol] = by_symbol.get(symbol, 0) + 1

    return {
        "total_entries": len(entries),
        "total_decisions": len(decisions),
        "by_type": by_type,
        "top_symbols": sorted(by_symbol.items(), key=lambda x: x[1], reverse=True)[:10],
    }
