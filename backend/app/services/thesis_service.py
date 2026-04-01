"""Thesis workflow helpers."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from app.services.inbox_service import get_inbox, update_inbox_item_state
from app.services.market_data import market_data_service
from app.services.store import store
from app.services.technical_analysis import compute_all_indicators


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_numeric_level(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)", text or "")
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def list_theses(user_id: str, tenant_id: str | None = None, symbol: str | None = None) -> list[dict]:
    theses = store.get_theses(user_id, tenant_id)
    if symbol:
        symbol = symbol.upper()
        theses = [thesis for thesis in theses if thesis.get("symbol", "").upper() == symbol]
    return sorted(theses, key=lambda thesis: thesis.get("updated_at", ""), reverse=True)


async def create_thesis_from_inbox_item(
    user_id: str,
    inbox_item: dict,
    tenant_id: str | None = None,
    *,
    override: dict | None = None,
) -> tuple[dict, dict]:
    now = _iso_now()
    primary_symbol = inbox_item.get("primary_symbol") or (inbox_item.get("symbols") or [None])[0]
    thesis = store.create_thesis(
        user_id,
        {
            "id": str(uuid.uuid4()),
            "symbol": primary_symbol or "SPY",
            "stance": "bear" if inbox_item.get("kind") == "risk_alert" else "bull",
            "conviction": max(0.35, float(inbox_item.get("confidence", 0.5))),
            "horizon": inbox_item.get("horizon", "medium"),
            "entry_zone": "",
            "invalidation": "",
            "catalysts": [inbox_item.get("why_now", "")] if inbox_item.get("why_now") else [],
            "risks": [evidence.get("summary", "") for evidence in inbox_item.get("evidence", [])[:2]],
            "notes": inbox_item.get("summary", ""),
            "status": "active",
            "review_state": "validating",
            "linked_inbox_ids": [inbox_item["id"]],
            "created_at": now,
            "updated_at": now,
            **(override or {}),
        },
        tenant_id,
    )
    event = store.add_thesis_event(
        user_id,
        thesis["id"],
        {
            "event_type": "created",
            "summary": f"Created from inbox item: {inbox_item.get('title', 'Insight')}",
            "review_state": thesis["review_state"],
            "metadata": {"inbox_item_id": inbox_item["id"]},
            "created_at": now,
        },
        tenant_id,
    )
    update_inbox_item_state(
        user_id,
        inbox_item["id"],
        "link_thesis",
        tenant_id,
        thesis_id=thesis["id"],
    )
    return thesis, event


def create_thesis(
    user_id: str, data: dict, tenant_id: str | None = None
) -> tuple[dict, dict]:
    now = _iso_now()
    thesis = store.create_thesis(
        user_id,
        {
            "id": str(uuid.uuid4()),
            "status": "active",
            "review_state": "validating",
            "linked_inbox_ids": data.get("linked_inbox_ids", []),
            "created_at": now,
            "updated_at": now,
            **data,
        },
        tenant_id,
    )
    event = store.add_thesis_event(
        user_id,
        thesis["id"],
        {
            "event_type": "created",
            "summary": "Thesis created manually",
            "review_state": thesis["review_state"],
            "metadata": {},
            "created_at": now,
        },
        tenant_id,
    )
    return thesis, event


def update_thesis(
    user_id: str, thesis_id: str, data: dict, tenant_id: str | None = None
) -> dict | None:
    updates = {k: v for k, v in data.items() if v is not None}
    if not updates:
        return store.get_thesis(user_id, thesis_id, tenant_id)
    updates["updated_at"] = _iso_now()
    thesis = store.update_thesis(user_id, thesis_id, updates, tenant_id)
    if thesis:
        store.add_thesis_event(
            user_id,
            thesis_id,
            {
                "event_type": "updated",
                "summary": "Thesis updated",
                "review_state": thesis.get("review_state"),
                "metadata": updates,
                "created_at": updates["updated_at"],
            },
            tenant_id,
        )
    return thesis


async def review_thesis(
    user_id: str,
    thesis_id: str,
    tenant_id: str | None = None,
    *,
    notes: str = "",
) -> dict:
    thesis = store.get_thesis(user_id, thesis_id, tenant_id)
    if not thesis:
        raise ValueError("Thesis not found")

    symbol = thesis.get("symbol", "").upper()
    quote = await market_data_service.get_quote(symbol) if symbol else None
    history = await market_data_service.get_history(symbol, period="6mo", interval="1d") if symbol else []
    technical = None
    if history and len(history) >= 30:
        technical = compute_all_indicators([point["close"] for point in history])

    inbox_payload = await get_inbox(user_id, tenant_id, symbol=symbol)
    supporting_items = inbox_payload["items"][:3]

    review_state = "validating"
    invalidation_level = _extract_numeric_level(thesis.get("invalidation", ""))
    current_price = float(quote.get("price", 0.0)) if isinstance(quote, dict) else 0.0
    bearish_pressure = technical and technical.get("overall_signal") == "bearish"
    risk_items = sum(1 for item in supporting_items if item.get("kind") == "risk_alert")

    if invalidation_level and current_price:
        if thesis.get("stance") == "bull" and current_price <= invalidation_level:
            review_state = "broken"
        elif thesis.get("stance") == "bear" and current_price >= invalidation_level:
            review_state = "broken"
    if review_state != "broken" and (bearish_pressure or risk_items >= 2):
        review_state = "at_risk"

    updated = store.update_thesis(
        user_id,
        thesis_id,
        {
            "review_state": review_state,
            "updated_at": _iso_now(),
            "notes": f"{thesis.get('notes', '')}\n\n{notes}".strip() if notes else thesis.get("notes", ""),
        },
        tenant_id,
    )
    event = store.add_thesis_event(
        user_id,
        thesis_id,
        {
            "event_type": "review",
            "summary": notes or f"Review completed with state {review_state}",
            "review_state": review_state,
            "metadata": {
                "current_price": current_price,
                "technical_signal": technical.get("overall_signal") if technical else None,
                "supporting_item_count": len(supporting_items),
            },
            "created_at": _iso_now(),
        },
        tenant_id,
    )
    return {"thesis": updated, "event": event, "supporting_items": supporting_items}
