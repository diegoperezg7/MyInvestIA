"""Structured event builder for inbox, thesis review, and briefings."""

from __future__ import annotations

from datetime import datetime, timezone


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event_key(event_type: str, symbol: str | None, title: str) -> str:
    base = f"{event_type}:{symbol or 'macro'}:{title}".lower()
    return base.replace(" ", "-")[:120]


def build_events(
    *,
    symbols: list[str],
    calendar: dict | None,
    filings_by_symbol: dict[str, dict] | None = None,
    insiders_by_symbol: dict[str, dict] | None = None,
    alerts: list[dict] | None = None,
    sentiment_shifts: list[dict] | None = None,
) -> list[dict]:
    events: list[dict] = []
    seen: set[str] = set()
    tracked = {symbol.upper() for symbol in symbols if symbol}

    def add_event(event: dict) -> None:
        key = _event_key(
            event.get("event_type", "event"),
            event.get("symbol"),
            event.get("title", ""),
        )
        if key in seen:
            return
        seen.add(key)
        events.append(event)

    for event in (calendar or {}).get("events", [])[:8]:
        add_event(
            {
                "id": _event_key("macro", None, event.get("event", "")),
                "event_type": "macro",
                "title": event.get("event", "Macro event"),
                "description": f"{event.get('country', '')} {event.get('impact', 'medium')} impact",
                "symbol": None,
                "event_at": f"{event.get('date', '')}T{event.get('time', '00:00')}:00",
                "importance": "high" if event.get("impact") == "high" else "medium",
                "source": "economic_calendar",
                "metadata": event,
            }
        )

    for earning in (calendar or {}).get("earnings", [])[:12]:
        symbol = (earning.get("symbol") or "").upper()
        if tracked and symbol not in tracked:
            continue
        add_event(
            {
                "id": _event_key("earnings", symbol, earning.get("date", "")),
                "event_type": "earnings",
                "title": f"{symbol} earnings",
                "description": "Upcoming earnings catalyst",
                "symbol": symbol,
                "event_at": f"{earning.get('date', '')}T00:00:00",
                "importance": "high",
                "source": "economic_calendar",
                "metadata": earning,
            }
        )

    for symbol, filings in (filings_by_symbol or {}).items():
        for filing in filings.get("filings", [])[:2]:
            add_event(
                {
                    "id": _event_key("filing", symbol, filing.get("accession_number", "")),
                    "event_type": "filing",
                    "title": f"{symbol} {filing.get('form', 'SEC filing')}",
                    "description": filing.get("description") or filing.get("items") or "SEC filing detected",
                    "symbol": symbol,
                    "event_at": filing.get("filed_at", _iso_now()),
                    "importance": "medium",
                    "source": filings.get("source", "sec"),
                    "url": filing.get("url"),
                    "metadata": filing,
                }
            )

    for symbol, data in (insiders_by_symbol or {}).items():
        for txn in data.get("transactions", [])[:2]:
            add_event(
                {
                    "id": _event_key(
                        "insider",
                        symbol,
                        f"{txn.get('insider_name', '')}-{txn.get('filing_date', '')}",
                    ),
                    "event_type": "insider",
                    "title": f"{symbol} insider {txn.get('transaction_type', 'activity')}",
                    "description": txn.get("relation") or txn.get("source") or "Insider activity",
                    "symbol": symbol,
                    "event_at": txn.get("filing_date", _iso_now()),
                    "importance": "medium",
                    "source": txn.get("source", data.get("source", "insider")),
                    "url": txn.get("url"),
                    "metadata": txn,
                }
            )

    for alert in alerts or []:
        severity = str(alert.get("severity", "medium"))
        if severity not in {"high", "critical"}:
            continue
        symbol = (alert.get("asset_symbol") or "").upper() or None
        add_event(
            {
                "id": _event_key("alert", symbol, alert.get("title", "")),
                "event_type": "alert",
                "title": alert.get("title", "Alert"),
                "description": alert.get("reasoning") or alert.get("description") or "Live alert",
                "symbol": symbol,
                "event_at": alert.get("created_at", _iso_now()),
                "importance": "high" if severity == "critical" else "medium",
                "source": "alerts_engine",
                "metadata": alert,
            }
        )

    for shift in sentiment_shifts or []:
        symbol = (shift.get("symbol") or "").upper() or None
        add_event(
            {
                "id": _event_key("sentiment", symbol, shift.get("title", "")),
                "event_type": "sentiment",
                "title": shift.get("title", "Sentiment shift"),
                "description": shift.get("description") or shift.get("summary") or "Sentiment regime moved materially",
                "symbol": symbol,
                "event_at": shift.get("created_at", _iso_now()),
                "importance": "medium",
                "source": shift.get("source", "sentiment"),
                "metadata": shift,
            }
        )

    def sort_key(event: dict) -> tuple[int, str]:
        importance = {"high": 0, "medium": 1, "low": 2}.get(
            str(event.get("importance", "medium")),
            1,
        )
        return importance, event.get("event_at", "")

    return sorted(events, key=sort_key)[:20]
