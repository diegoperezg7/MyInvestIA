"""Research / Quant Lab ranking service."""

from __future__ import annotations

import asyncio
import statistics
import uuid
from datetime import datetime, timezone

from app.services.enhanced_sentiment_service import get_enhanced_sentiment
from app.services.fundamentals_service import get_fundamentals
from app.services.insider_service import get_insider_activity
from app.services.macro_intelligence import get_all_macro_indicators
from app.services.market_data import market_data_service
from app.services.quant_scoring import compute_quant_scores
from app.services.store import store

DEFAULT_UNIVERSE = ["AAPL", "MSFT", "NVDA", "SPY", "QQQ"]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _to_100(raw: float) -> float:
    return _clip((raw + 1) * 50)


def _quality_score(fundamentals: dict | None) -> float:
    if not fundamentals:
        return 50.0
    ratios = fundamentals.get("ratios", {})
    growth = fundamentals.get("growth", {})
    roe = float(ratios.get("roe", 0.0) or 0.0)
    margins = float(ratios.get("profit_margins", 0.0) or 0.0)
    growth_score = float(growth.get("earnings_growth", 0.0) or 0.0)
    score = 50 + roe * 25 + margins * 25 + growth_score * 20
    return _clip(score)


def _value_score(fundamentals: dict | None) -> float:
    if not fundamentals:
        return 50.0
    ratios = fundamentals.get("ratios", {})
    pe = float(ratios.get("pe_forward") or ratios.get("pe_trailing") or 0.0)
    pb = float(ratios.get("price_to_book") or 0.0)
    ps = float(ratios.get("price_to_sales") or 0.0)
    penalties = 0.0
    penalties += min(pe / 40, 1.5) * 25 if pe > 0 else 0
    penalties += min(pb / 10, 1.5) * 20 if pb > 0 else 0
    penalties += min(ps / 12, 1.5) * 15 if ps > 0 else 0
    return _clip(100 - penalties)


def _revision_score(fundamentals: dict | None) -> float:
    if not fundamentals:
        return 50.0
    growth = fundamentals.get("growth", {})
    revenue_growth = float(growth.get("revenue_growth", 0.0) or 0.0)
    earnings_growth = float(growth.get("earnings_growth", 0.0) or 0.0)
    return _clip(50 + revenue_growth * 30 + earnings_growth * 40)


def _insider_accumulation_score(insiders: dict | None) -> float:
    if not insiders:
        return 50.0
    score = 50.0
    buy_value = 0.0
    sell_value = 0.0
    for txn in insiders.get("transactions", []):
        txn_type = str(txn.get("transaction_type", "")).lower()
        value = float(txn.get("value", 0.0) or 0.0)
        if any(token in txn_type for token in ["buy", "purchase", "acquired"]):
            buy_value += value
        elif any(token in txn_type for token in ["sell", "sale", "disposed"]):
            sell_value += value
    if buy_value or sell_value:
        ratio = (buy_value - sell_value) / max(buy_value + sell_value, 1.0)
        score += ratio * 35
    return _clip(score)


def _risk_score(quant_scores: dict) -> float:
    risk_metrics = quant_scores.get("risk_metrics", {})
    sharpe = float(risk_metrics.get("sharpe_ratio", 0.0) or 0.0)
    drawdown = float(risk_metrics.get("max_drawdown", 0.0) or 0.0)
    vol = float(risk_metrics.get("historical_volatility", 0.0) or 0.0)
    score = 55 + sharpe * 8 - drawdown * 120 - vol * 20
    return _clip(score)


def _factor_set(
    quant_scores: dict,
    sentiment: dict | None,
    fundamentals: dict | None,
    insiders: dict | None,
) -> dict:
    quant_factors = quant_scores.get("factors", {})
    momentum = statistics.fmean(
        [
            _to_100(float(quant_factors.get("trend", 0.0))),
            _to_100(float(quant_factors.get("momentum", 0.0))),
            _to_100(float(quant_factors.get("volume", 0.0))),
        ]
    )
    sentiment_score = 50.0
    if sentiment:
        sentiment_score = _clip(50 + float(sentiment.get("unified_score", 0.0)) * 50)

    return {
        "momentum": round(momentum, 2),
        "quality": round(_quality_score(fundamentals), 2),
        "value": round(_value_score(fundamentals), 2),
        "revisions": round(_revision_score(fundamentals), 2),
        "sentiment": round(sentiment_score, 2),
        "insider_accumulation": round(_insider_accumulation_score(insiders), 2),
        "risk": round(_risk_score(quant_scores), 2),
    }


async def _build_symbol_research(symbol: str, macro_indicators: list[dict]) -> dict | None:
    history, quote, sentiment, fundamentals, insiders = await asyncio.gather(
        market_data_service.get_history(symbol, period="1y", interval="1d"),
        market_data_service.get_quote(symbol),
        get_enhanced_sentiment(symbol),
        get_fundamentals(symbol),
        get_insider_activity(symbol),
        return_exceptions=True,
    )

    if isinstance(history, Exception) or not history or len(history) < 30:
        return None

    quant_scores = compute_quant_scores(
        history=history,
        macro_indicators=macro_indicators,
        enhanced_sentiment=None if isinstance(sentiment, Exception) else sentiment,
    )
    sentiment_data = None if isinstance(sentiment, Exception) else sentiment
    fundamentals_data = None if isinstance(fundamentals, Exception) else fundamentals
    insiders_data = None if isinstance(insiders, Exception) else insiders
    quote_data = {} if isinstance(quote, Exception) or quote is None else quote
    factor_set = _factor_set(
        quant_scores,
        sentiment_data,
        fundamentals_data,
        insiders_data,
    )
    composite = statistics.fmean(factor_set.values())

    return {
        "symbol": symbol,
        "name": quote_data.get("name") or (fundamentals_data or {}).get("company_info", {}).get("name", symbol),
        "quote": quote_data,
        "factors_v1": factor_set,
        "quant_scores": quant_scores,
        "composite_score_v1": round(composite, 2),
        "thesis_id": None,
        "inbox_item_id": None,
    }


def _resolve_universe(
    user_id: str, tenant_id: str | None = None, extra_symbols: list[str] | None = None
) -> list[str]:
    symbols: set[str] = set()
    for holding in store.get_holdings(user_id, tenant_id):
        symbols.add(holding["symbol"].upper())
    for watchlist in store.get_watchlists(user_id, tenant_id):
        for asset in watchlist.get("assets", []):
            symbols.add(asset["symbol"].upper())
    for symbol in extra_symbols or []:
        if symbol:
            symbols.add(symbol.upper())
    if not symbols:
        symbols.update(DEFAULT_UNIVERSE)
    return list(symbols)[:20]


def _attach_workflow_links(
    user_id: str, tenant_id: str | None, ranking: dict
) -> dict:
    theses = store.get_theses(user_id, tenant_id)
    items = store.get_inbox_items(user_id, tenant_id)
    symbol = ranking["symbol"]
    linked_thesis = next((thesis for thesis in theses if thesis.get("symbol") == symbol), None)
    linked_item = next(
        (
            item
            for item in items
            if item.get("primary_symbol") == symbol and item.get("status") != "dismissed"
        ),
        None,
    )
    ranking["thesis_id"] = linked_thesis.get("id") if linked_thesis else None
    ranking["inbox_item_id"] = linked_item.get("id") if linked_item else None
    return ranking


def _snapshot_timestamp(snapshot: dict) -> datetime | None:
    captured_at = snapshot.get("captured_at")
    try:
        return datetime.fromisoformat(str(captured_at).replace("Z", "+00:00"))
    except ValueError:
        return None


def _ranking_price(ranking: dict) -> float:
    return float(ranking.get("current_price") or ranking.get("reference_price") or 0.0)


def _build_backtest_lite(snapshot: dict, latest_snapshot: dict | None = None) -> list[dict]:
    if not latest_snapshot or snapshot.get("id") == latest_snapshot.get("id"):
        return []

    horizons = {"1W": 7, "1M": 30, "3M": 90}
    snapshot_ts = _snapshot_timestamp(snapshot)
    latest_ts = _snapshot_timestamp(latest_snapshot)
    if snapshot_ts is None or latest_ts is None or latest_ts <= snapshot_ts:
        return []

    latest_prices = {
        str(ranking.get("symbol") or "").upper(): _ranking_price(ranking)
        for ranking in latest_snapshot.get("rankings", [])
        if str(ranking.get("symbol") or "").strip() and _ranking_price(ranking) > 0
    }
    if not latest_prices:
        return []

    results: list[dict] = []
    for label, days in horizons.items():
        if (latest_ts - snapshot_ts).days < days:
            continue

        returns: list[float] = []
        for ranking in snapshot.get("rankings", [])[:5]:
            symbol = str(ranking.get("symbol") or "").upper()
            price_then = float(ranking.get("reference_price", 0.0) or 0.0)
            price_now = latest_prices.get(symbol, 0.0)
            if price_then > 0 and price_now > 0:
                returns.append((price_now - price_then) / price_then)
        if not returns:
            continue
        results.append(
            {
                "horizon": label,
                "average_return": round(statistics.fmean(returns), 4),
                "median_return": round(statistics.median(returns), 4),
                "hit_rate": round(sum(1 for value in returns if value > 0) / len(returns), 4),
                "samples": len(returns),
            }
        )
    return results


async def get_rankings(
    user_id: str,
    tenant_id: str | None = None,
    *,
    extra_symbols: list[str] | None = None,
    save_snapshot: bool = False,
) -> dict:
    universe = _resolve_universe(user_id, tenant_id, extra_symbols)
    macro_indicators = await get_all_macro_indicators()
    results = await asyncio.gather(
        *[_build_symbol_research(symbol, macro_indicators) for symbol in universe],
        return_exceptions=True,
    )

    rankings = []
    for result in results:
        if isinstance(result, Exception) or not result:
            continue
        linked = _attach_workflow_links(user_id, tenant_id, result)
        rankings.append(
            {
                "symbol": linked["symbol"],
                "name": linked["name"],
                "composite_score": linked["composite_score_v1"],
                "confidence": linked["quant_scores"].get("confidence", 0.0),
                "verdict": linked["quant_scores"].get("verdict", "neutral"),
                "factors": linked["factors_v1"],
                "thesis_id": linked["thesis_id"],
                "inbox_item_id": linked["inbox_item_id"],
                "reference_price": linked["quote"].get("price", 0.0),
                "current_price": linked["quote"].get("price", 0.0),
            }
        )

    rankings.sort(key=lambda item: (-item["composite_score"], -item["confidence"], item["symbol"]))
    snapshot_id = None
    if save_snapshot and rankings:
        captured_at = _iso_now()
        snapshot = store.save_research_snapshot(
            user_id,
            {
                "id": str(uuid.uuid4()),
                "name": f"Snapshot {captured_at}",
                "universe": universe,
                "rankings": rankings,
                "validation": [],
                "captured_at": captured_at,
            },
            tenant_id,
        )
        snapshot_id = snapshot["id"]

    return {
        "rankings": rankings,
        "universe": universe,
        "generated_at": _iso_now(),
        "snapshot_id": snapshot_id,
        "screens": store.get_research_screens(user_id, tenant_id),
    }


async def get_symbol_factors(symbol: str) -> dict:
    macro_indicators = await get_all_macro_indicators()
    result = await _build_symbol_research(symbol.upper(), macro_indicators)
    if not result:
        return {
            "symbol": symbol.upper(),
            "generated_at": _iso_now(),
            "composite_score": 0.0,
            "confidence": 0.0,
            "verdict": "neutral",
            "regime": "unknown",
            "adx": 0.0,
            "weights": {},
            "factors": {
                "momentum": 0.0,
                "quality": 0.0,
                "value": 0.0,
                "revisions": 0.0,
                "sentiment": 0.0,
                "insider_accumulation": 0.0,
                "risk": 0.0,
            },
            "support_resistance": {},
            "candlestick_patterns": [],
            "risk_metrics": {},
            "factor_agreement": 0.0,
        }
    quant_scores = result["quant_scores"]
    return {
        "symbol": symbol.upper(),
        "generated_at": _iso_now(),
        "composite_score": result["composite_score_v1"],
        "confidence": quant_scores.get("confidence", 0.0),
        "verdict": quant_scores.get("verdict", "neutral"),
        "regime": quant_scores.get("regime", "unknown"),
        "adx": quant_scores.get("adx", 0.0),
        "weights": quant_scores.get("weights", {}),
        "factors": result["factors_v1"],
        "support_resistance": quant_scores.get("support_resistance", {}),
        "candlestick_patterns": quant_scores.get("candlestick_patterns", []),
        "risk_metrics": quant_scores.get("risk_metrics", {}),
        "factor_agreement": quant_scores.get("factor_agreement", 0.0),
    }


def save_screen(user_id: str, data: dict, tenant_id: str | None = None) -> dict:
    now = _iso_now()
    return store.save_research_screen(
        user_id,
        {
            "id": data.get("id", str(uuid.uuid4())),
            "name": data.get("name", "Saved screen"),
            "symbols": [symbol.upper() for symbol in data.get("symbols", [])],
            "notes": data.get("notes", ""),
            "created_at": data.get("created_at", now),
            "updated_at": now,
        },
        tenant_id,
    )


def list_snapshots(user_id: str, tenant_id: str | None = None) -> dict:
    snapshots = store.get_research_snapshots(user_id, tenant_id)
    latest_snapshot = max(
        snapshots,
        key=lambda snapshot: _snapshot_timestamp(snapshot) or datetime.min.replace(tzinfo=timezone.utc),
        default=None,
    )
    enriched = []
    for snapshot in snapshots:
        enriched.append({**snapshot, "validation": _build_backtest_lite(snapshot, latest_snapshot)})
    return {"snapshots": enriched, "total": len(enriched)}
