"""Normalization helpers shared by the data provider layer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def normalize_symbol(symbol: str) -> str:
    return (symbol or "").strip().upper()


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value in (None, "", "."):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value in (None, "", "."):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def to_utc_iso(value: Any = None) -> str:
    if value in (None, ""):
        return datetime.now(timezone.utc).isoformat()
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()

    text = str(value).strip()
    if not text:
        return datetime.now(timezone.utc).isoformat()
    if text.isdigit():
        return datetime.fromtimestamp(int(text), tz=timezone.utc).isoformat()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(
            timezone.utc
        ).isoformat()
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
            return parsed.isoformat()
        except ValueError:
            continue

    return datetime.now(timezone.utc).isoformat()


def to_unix_timestamp(value: Any = None) -> int:
    return int(datetime.fromisoformat(to_utc_iso(value)).timestamp())


def normalize_quote_payload(
    raw: dict,
    *,
    symbol: str,
    provider_id: str,
    provider_name: str,
    retrieval_mode: str,
) -> dict | None:
    if not raw:
        return None
    price = _safe_float(raw.get("price"))
    if price <= 0:
        return None
    return {
        "symbol": normalize_symbol(raw.get("symbol") or symbol),
        "name": str(raw.get("name") or normalize_symbol(symbol)),
        "price": round(price, 4),
        "change_percent": round(_safe_float(raw.get("change_percent")), 2),
        "volume": _safe_float(raw.get("volume")),
        "previous_close": round(_safe_float(raw.get("previous_close")), 4),
        "market_cap": _safe_float(raw.get("market_cap")),
        "currency": str(raw.get("currency") or "USD"),
        "source": provider_name,
        "source_provider": provider_id,
        "retrieval_mode": str(raw.get("retrieval_mode") or retrieval_mode),
        "as_of": to_utc_iso(raw.get("as_of") or raw.get("timestamp")),
    }


def normalize_history_rows(
    rows: list[dict],
    *,
    provider_id: str,
    retrieval_mode: str,
) -> list[dict]:
    normalized: list[dict] = []
    for row in rows or []:
        close = _safe_float(row.get("close"))
        if close <= 0:
            continue
        normalized.append(
            {
                "date": to_utc_iso(row.get("date")),
                "open": round(_safe_float(row.get("open"), close), 4),
                "high": round(_safe_float(row.get("high"), close), 4),
                "low": round(_safe_float(row.get("low"), close), 4),
                "close": round(close, 4),
                "volume": _safe_int(row.get("volume")),
                "source_provider": provider_id,
                "retrieval_mode": retrieval_mode,
            }
        )
    return normalized


def normalize_macro_indicator(
    *,
    name: str,
    ticker: str,
    value: Any,
    previous_close: Any,
    category: str,
    trend: str,
    impact_description: str,
    provider_id: str,
    provider_name: str,
    retrieval_mode: str,
    as_of: Any = None,
) -> dict | None:
    current = _safe_float(value)
    if current == 0 and current != _safe_float(previous_close):
        return None
    previous = _safe_float(previous_close, current)
    change_pct = ((current - previous) / previous * 100) if previous else 0.0
    return {
        "name": name,
        "ticker": ticker,
        "value": round(current, 4),
        "change_percent": round(change_pct, 2),
        "previous_close": round(previous, 4),
        "trend": trend,
        "impact_description": impact_description,
        "category": category,
        "source": provider_name,
        "source_provider": provider_id,
        "retrieval_mode": retrieval_mode,
        "as_of": to_utc_iso(as_of),
    }


def normalize_news_article(
    article: dict,
    *,
    provider_id: str,
    retrieval_mode: str,
    default_category: str = "news",
) -> dict | None:
    headline = str(article.get("headline") or "").strip()
    if not headline:
        return None
    return {
        "headline": headline,
        "summary": str(article.get("summary") or "").strip(),
        "source": str(article.get("source") or provider_id.upper()),
        "source_provider": str(article.get("source_provider") or provider_id),
        "source_category": str(article.get("source_category") or default_category),
        "url": str(article.get("url") or ""),
        "datetime": to_unix_timestamp(article.get("datetime")),
        "retrieval_mode": str(article.get("retrieval_mode") or retrieval_mode),
        "author": article.get("author"),
        "score": article.get("score"),
        "num_comments": article.get("num_comments"),
        "sentiment_label": article.get("sentiment_label"),
    }


def normalize_fundamentals_payload(
    payload: dict,
    *,
    symbol: str,
    provider_id: str,
    provider_name: str,
    retrieval_mode: str,
) -> dict | None:
    if not payload:
        return None
    return {
        **payload,
        "symbol": normalize_symbol(payload.get("symbol") or symbol),
        "source": provider_name,
        "source_provider": provider_id,
        "retrieval_mode": retrieval_mode,
        "generated_at": to_utc_iso(payload.get("generated_at")),
    }


def normalize_filings_payload(
    payload: dict,
    *,
    symbol: str,
    provider_id: str,
    provider_name: str,
    retrieval_mode: str,
) -> dict | None:
    if not payload:
        return None
    filings = []
    for item in payload.get("filings", []) or []:
        filings.append(
            {
                "form": str(item.get("form") or ""),
                "filed_at": to_utc_iso(item.get("filed_at")),
                "description": str(item.get("description") or ""),
                "items": str(item.get("items") or ""),
                "url": str(item.get("url") or ""),
                "accession_number": str(item.get("accession_number") or ""),
            }
        )
    return {
        "symbol": normalize_symbol(payload.get("symbol") or symbol),
        "company_name": str(payload.get("company_name") or normalize_symbol(symbol)),
        "cik": str(payload.get("cik") or ""),
        "source": provider_name,
        "source_provider": provider_id,
        "retrieval_mode": retrieval_mode,
        "filings": filings,
        "generated_at": to_utc_iso(payload.get("generated_at")),
    }
