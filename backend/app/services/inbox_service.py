"""Inbox / insight assembly service."""

from __future__ import annotations

import asyncio
import logging
import math
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.schemas.workflow import AssistantMode
from app.services.alert_scorer import scan_symbols
from app.services.event_engine import build_events
from app.services.market_data import market_data_service
from app.services.news_aggregator import get_ai_analyzed_feed
from app.services.portfolio_risk import calculate_portfolio_risk
from app.services.profile_service import load_profile
from app.services.store import store

logger = logging.getLogger(__name__)

INBOX_TTL_SECONDS = 600
DEFAULT_UNIVERSE = [
    {"symbol": "AAPL", "type": "stock"},
    {"symbol": "MSFT", "type": "stock"},
    {"symbol": "NVDA", "type": "stock"},
    {"symbol": "SPY", "type": "etf"},
    {"symbol": "QQQ", "type": "etf"},
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().isoformat()


def _expires_at(seconds: int = INBOX_TTL_SECONDS) -> str:
    return (_utc_now() + timedelta(seconds=seconds)).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _clip(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _impact_label(value: float) -> str:
    if value >= 0.7:
        return "high"
    if value <= 0.35:
        return "low"
    return "medium"


def _horizon_from_text(value: str) -> str:
    raw = (value or "").lower()
    if raw in {"immediate", "short", "medium", "long"}:
        return raw
    if any(token in raw for token in ["today", "breaking", "earnings", "macro", "alerta"]):
        return "immediate"
    if any(token in raw for token in ["week", "short", "corto"]):
        return "short"
    if any(token in raw for token in ["long", "largo"]):
        return "long"
    return "medium"


def _severity_to_urgency(value: str | None) -> float:
    return {
        "critical": 1.0,
        "high": 0.85,
        "medium": 0.6,
        "low": 0.35,
    }.get((value or "medium").lower(), 0.5)


class InsightAssembler:
    """Normalizes portfolio, alerts, news, risk, events, and legacy AI layers into Inbox items."""

    def __init__(self, user_id: str, tenant_id: str | None = None):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.profile = load_profile(user_id, tenant_id)
        self.holdings = store.get_holdings(user_id, tenant_id)
        self.watchlists = store.get_watchlists(user_id, tenant_id)
        self.previous_items = store.get_inbox_items(user_id, tenant_id)
        self.holding_symbols = {holding["symbol"].upper() for holding in self.holdings}
        self.watchlist_symbols = {
            asset["symbol"].upper()
            for watchlist in self.watchlists
            for asset in watchlist.get("assets", [])
        }
        self.symbol_payload = self._build_symbol_payload()
        self.holding_weights: dict[str, float] = {}

    def _build_symbol_payload(self) -> list[dict]:
        payload: list[dict] = []
        seen: set[str] = set()
        for holding in self.holdings:
            symbol = holding["symbol"].upper()
            if symbol not in seen:
                payload.append({"symbol": symbol, "type": holding.get("type", "stock")})
                seen.add(symbol)
        for watchlist in self.watchlists:
            for asset in watchlist.get("assets", []):
                symbol = asset["symbol"].upper()
                if symbol not in seen:
                    payload.append({"symbol": symbol, "type": asset.get("type", "stock")})
                    seen.add(symbol)
        return payload or list(DEFAULT_UNIVERSE)

    async def _build_holding_weights(self) -> None:
        values: dict[str, float] = {}
        for holding in self.holdings:
            try:
                quote = await market_data_service.get_quote(
                    holding["symbol"], holding.get("type")
                )
            except Exception:
                quote = None
            price = quote.get("price") if isinstance(quote, dict) else holding.get("avg_buy_price", 0)
            values[holding["symbol"].upper()] = float(price or 0) * float(holding.get("quantity", 0))
        total = sum(values.values())
        if total > 0:
            self.holding_weights = {
                symbol: value / total for symbol, value in values.items() if value > 0
            }

    async def _build_risk_context(self) -> dict:
        if not self.holdings:
            return {}
        holdings_for_risk = []
        for holding in self.holdings:
            try:
                quote = await market_data_service.get_quote(
                    holding["symbol"], holding.get("type")
                )
            except Exception:
                quote = None
            price = quote.get("price") if isinstance(quote, dict) else holding.get("avg_buy_price", 0)
            current_value = float(price or 0) * float(holding.get("quantity", 0))
            if current_value > 0:
                holdings_for_risk.append(
                    {
                        "symbol": holding["symbol"].upper(),
                        "quantity": holding.get("quantity", 0),
                        "current_value": current_value,
                    }
                )
        if not holdings_for_risk:
            return {}
        return await calculate_portfolio_risk(holdings_for_risk)

    async def assemble(self) -> dict:
        from app.services.briefing_service import generate_briefing as legacy_briefing
        from app.services.economic_calendar import fetch_economic_calendar
        from app.services.macro_context_service import get_macro_context
        from app.services.macro_intelligence import get_all_macro_indicators, get_macro_summary
        from app.services.recommendations_service import (
            generate_recommendations as legacy_recommendations,
        )
        from app.services.insider_service import get_insider_activity
        from app.services.sec_service import get_company_filings

        async def safe_call(coro, fallback):
            try:
                return await coro
            except Exception as exc:
                logger.warning("Insight assembler subtask failed: %s", exc)
                return fallback

        await self._build_holding_weights()
        symbols = [item["symbol"] for item in self.symbol_payload]
        primary_symbols = symbols[:4]

        async with asyncio.TaskGroup() as tg:
            recommendations_task = tg.create_task(
                safe_call(legacy_recommendations(self.user_id), {"recommendations": [], "mood_score": 0.0, "market_mood": ""})
            )
            briefing_task = tg.create_task(
                safe_call(legacy_briefing(self.user_id), {"briefing": "", "suggestions": []})
            )
            alerts_task = tg.create_task(safe_call(scan_symbols(self.symbol_payload), []))
            news_task = tg.create_task(
                safe_call(
                    get_ai_analyzed_feed(limit=40),
                    {"articles": [], "top_narratives": [], "source_health": {}},
                )
            )
            macro_task = tg.create_task(safe_call(get_all_macro_indicators(), []))
            macro_context_task = tg.create_task(safe_call(get_macro_context(), {}))
            calendar_task = tg.create_task(
                safe_call(fetch_economic_calendar(), {"events": [], "earnings": [], "sources": []})
            )
            risk_task = tg.create_task(safe_call(self._build_risk_context(), {}))
            filings_tasks = {
                symbol: tg.create_task(
                    safe_call(
                        get_company_filings(symbol),
                        {"symbol": symbol, "source": "sec", "filings": []},
                    )
                )
                for symbol in primary_symbols
            }
            insider_tasks = {
                symbol: tg.create_task(
                    safe_call(
                        get_insider_activity(symbol),
                        {"symbol": symbol, "source": "insider", "transactions": []},
                    )
                )
                for symbol in primary_symbols
            }

        recommendations = recommendations_task.result()
        briefing = briefing_task.result()
        alerts = [alert.model_dump() if hasattr(alert, "model_dump") else alert for alert in alerts_task.result()]
        news_feed = news_task.result()
        macro_indicators = macro_task.result()
        macro_summary = get_macro_summary(macro_indicators)
        macro_context = macro_context_task.result()
        calendar = calendar_task.result()
        risk_context = risk_task.result() or {}
        filings_by_symbol = {
            symbol: task.result() for symbol, task in filings_tasks.items() if task.result()
        }
        insiders_by_symbol = {
            symbol: task.result() for symbol, task in insider_tasks.items() if task.result()
        }

        events = build_events(
            symbols=symbols,
            calendar=calendar,
            filings_by_symbol=filings_by_symbol,
            insiders_by_symbol=insiders_by_symbol,
            alerts=alerts,
            sentiment_shifts=self._build_sentiment_shift_events(news_feed),
        )

        candidates: list[dict] = []
        candidates.extend(self._from_recommendations(recommendations))
        candidates.extend(self._from_alerts(alerts))
        candidates.extend(self._from_risk(risk_context))
        candidates.extend(self._from_news(news_feed))
        candidates.extend(self._from_events(events))
        candidates.extend(self._from_macro(macro_summary, macro_context))
        candidates.extend(self._from_research_hooks(news_feed))

        enriched = self._finalize_items(candidates)
        store.replace_inbox_items(self.user_id, enriched, self.tenant_id)
        generated_at = enriched[0]["created_at"] if enriched else _iso_now()
        return {
            "items": enriched,
            "generated_at": generated_at,
            "cached_until": enriched[0]["expires_at"] if enriched else _expires_at(),
            "briefing": briefing,
            "events": events,
            "mood_score": float(recommendations.get("mood_score", 0.0)),
            "market_mood": recommendations.get("market_mood", ""),
        }

    def _build_sentiment_shift_events(self, news_feed: dict) -> list[dict]:
        shifts: list[dict] = []
        for article in news_feed.get("articles", [])[:6]:
            score = float(article.get("sentiment_score", 0.0))
            if abs(score) < 0.45:
                continue
            shifts.append(
                {
                    "symbol": (article.get("ticker_mentions") or [None])[0],
                    "title": article.get("headline", "Sentiment shift"),
                    "description": article.get("summary") or article.get("headline"),
                    "created_at": datetime.fromtimestamp(
                        float(article.get("datetime", 0) or 0), tz=timezone.utc
                    ).isoformat()
                    if article.get("datetime")
                    else _iso_now(),
                    "source": article.get("source_provider", article.get("source", "news")),
                }
            )
        return shifts

    def _from_recommendations(self, recommendations: dict) -> list[dict]:
        items: list[dict] = []
        for recommendation in recommendations.get("recommendations", [])[:8]:
            kind = recommendation.get("category", "opportunity")
            symbols = [symbol.upper() for symbol in recommendation.get("tickers", [])]
            evidence = [
                {
                    "category": "ai",
                    "source": "recommendations_engine",
                    "summary": recommendation.get("reasoning", ""),
                    "confidence": recommendation.get("confidence", 0.0),
                    "score": recommendation.get("confidence", 0.0),
                }
            ]
            items.append(
                {
                    "scope": self._resolve_scope(symbols[0] if symbols else None, kind),
                    "kind": kind,
                    "title": recommendation.get("title", "Recommendation"),
                    "summary": recommendation.get("reasoning", ""),
                    "why_now": recommendation.get("action", ""),
                    "symbols": symbols,
                    "primary_symbol": symbols[0] if symbols else None,
                    "confidence": float(recommendation.get("confidence", 0.0)),
                    "impact_score": 0.7 if kind in {"risk_alert", "opportunity", "rebalance"} else 0.55,
                    "horizon": _horizon_from_text(recommendation.get("urgency", "")),
                    "urgency_score": _severity_to_urgency(recommendation.get("urgency")),
                    "evidence": evidence,
                }
            )
        return items

    def _from_alerts(self, alerts: list[dict]) -> list[dict]:
        items: list[dict] = []
        for alert in alerts[:10]:
            symbol = (alert.get("asset_symbol") or "").upper() or None
            kind = "risk_alert" if alert.get("suggested_action") == "sell" else "opportunity"
            category = "price_volume" if alert.get("type") == "price" else "technical"
            items.append(
                {
                    "scope": self._resolve_scope(symbol, kind),
                    "kind": kind,
                    "title": alert.get("title", "Alert"),
                    "summary": alert.get("description", ""),
                    "why_now": alert.get("reasoning", ""),
                    "symbols": [symbol] if symbol else [],
                    "primary_symbol": symbol,
                    "confidence": float(alert.get("confidence", 0.0)),
                    "impact_score": 0.75,
                    "horizon": "immediate",
                    "urgency_score": _severity_to_urgency(alert.get("severity")),
                    "evidence": [
                        {
                            "category": category,
                            "source": "alerts_engine",
                            "summary": alert.get("reasoning") or alert.get("description", ""),
                            "confidence": float(alert.get("confidence", 0.0)),
                            "score": _severity_to_urgency(alert.get("severity")),
                        }
                    ],
                }
            )
        return items

    def _from_risk(self, risk_context: dict) -> list[dict]:
        if not risk_context:
            return []
        items: list[dict] = []
        concentration = risk_context.get("concentration", {})
        for alert in concentration.get("alerts", [])[:2]:
            symbol = alert.split()[0].upper() if alert else None
            items.append(
                {
                    "scope": "portfolio",
                    "kind": "risk_alert",
                    "title": f"Concentration risk on {symbol}",
                    "summary": alert,
                    "why_now": "Portfolio concentration is above the preferred limit.",
                    "symbols": [symbol] if symbol else [],
                    "primary_symbol": symbol,
                    "confidence": 0.82,
                    "impact_score": 0.85,
                    "horizon": "medium",
                    "urgency_score": 0.8,
                    "evidence": [
                        {
                            "category": "portfolio_risk",
                            "source": "portfolio_risk",
                            "summary": alert,
                            "confidence": 0.82,
                            "score": concentration.get("top3_concentration", 0.0),
                        }
                    ],
                }
            )
        for pair in risk_context.get("correlation", {}).get("high_correlations", [])[:2]:
            items.append(
                {
                    "scope": "portfolio",
                    "kind": "rebalance",
                    "title": f"Correlation cluster: {pair.get('pair', 'portfolio')}",
                    "summary": "Highly correlated positions reduce diversification.",
                    "why_now": f"Correlation at {pair.get('value', 0):.2f} increases drawdown sensitivity.",
                    "symbols": pair.get("pair", "").split("/"),
                    "primary_symbol": pair.get("pair", "").split("/")[0] if pair.get("pair") else None,
                    "confidence": 0.76,
                    "impact_score": 0.7,
                    "horizon": "medium",
                    "urgency_score": 0.65,
                    "evidence": [
                        {
                            "category": "portfolio_risk",
                            "source": "portfolio_risk",
                            "summary": f"High correlation pair at {pair.get('value', 0):.2f}",
                            "confidence": 0.76,
                            "score": abs(float(pair.get("value", 0))),
                        }
                    ],
                }
            )
        for scenario in risk_context.get("scenario_results", risk_context.get("stress_tests", []))[:1]:
            items.append(
                {
                    "scope": "portfolio",
                    "kind": "macro_shift",
                    "title": f"Scenario risk: {scenario.get('name', 'Stress test')}",
                    "summary": scenario.get("description", "Stress scenario"),
                    "why_now": f"Estimated loss {scenario.get('estimated_portfolio_loss_pct', 0):.2%} under this scenario.",
                    "symbols": list(self.holding_symbols)[:3],
                    "primary_symbol": None,
                    "confidence": 0.7,
                    "impact_score": 0.78,
                    "horizon": "medium",
                    "urgency_score": 0.6,
                    "evidence": [
                        {
                            "category": "portfolio_risk",
                            "source": "portfolio_risk",
                            "summary": scenario.get("description", "Stress scenario"),
                            "confidence": 0.7,
                            "score": abs(float(scenario.get("estimated_portfolio_loss_pct", 0))),
                        }
                    ],
                }
            )
        return items

    def _from_news(self, news_feed: dict) -> list[dict]:
        items: list[dict] = []
        tracked = self.holding_symbols | self.watchlist_symbols
        articles = news_feed.get("articles", [])
        if tracked:
            relevant = [
                article
                for article in articles
                if tracked.intersection(article.get("ticker_mentions", []))
            ]
        else:
            relevant = articles
        for article in relevant[:6]:
            symbols = [symbol.upper() for symbol in article.get("ticker_mentions", [])]
            score = float(article.get("sentiment_score", 0.0))
            category = (
                "social"
                if article.get("source_category") == "social"
                else "news"
            )
            items.append(
                {
                    "scope": self._resolve_scope(symbols[0] if symbols else None, "news"),
                    "kind": "social_signal" if category == "social" else "news",
                    "title": article.get("headline", "News item"),
                    "summary": article.get("summary") or article.get("headline", ""),
                    "why_now": f"{article.get('source', 'source')} · conf {(float(article.get('confidence', 0)) * 100):.0f}%",
                    "symbols": symbols,
                    "primary_symbol": symbols[0] if symbols else None,
                    "confidence": float(article.get("confidence", 0.0)),
                    "impact_score": 0.55 + min(abs(score), 0.3),
                    "horizon": "short",
                    "urgency_score": 0.55 + min(abs(score), 0.25),
                    "evidence": [
                        {
                            "category": category,
                            "source": article.get("source_provider", article.get("source", "news")),
                            "summary": article.get("headline", ""),
                            "url": article.get("url"),
                            "confidence": float(article.get("confidence", 0.0)),
                            "score": abs(score),
                        }
                    ],
                }
            )
        return items

    def _from_events(self, events: list[dict]) -> list[dict]:
        items: list[dict] = []
        for event in events[:6]:
            kind = "earnings_watch" if event.get("event_type") == "earnings" else event.get("event_type", "event")
            items.append(
                {
                    "scope": self._resolve_scope(event.get("symbol"), kind),
                    "kind": kind,
                    "title": event.get("title", "Event"),
                    "summary": event.get("description", ""),
                    "why_now": f"Scheduled at {event.get('event_at', '')}",
                    "symbols": [event["symbol"]] if event.get("symbol") else [],
                    "primary_symbol": event.get("symbol"),
                    "confidence": 0.7,
                    "impact_score": 0.68,
                    "horizon": "immediate",
                    "urgency_score": 0.72 if event.get("importance") == "high" else 0.58,
                    "evidence": [
                        {
                            "category": "macro_events" if event.get("event_type") == "macro" else "macro_events",
                            "source": event.get("source", "event_engine"),
                            "summary": event.get("description", ""),
                            "url": event.get("url"),
                            "confidence": 0.7,
                            "score": 0.68,
                        }
                    ],
                }
            )
        return items

    def _from_macro(self, macro_summary: dict, macro_context: dict) -> list[dict]:
        items: list[dict] = []
        if macro_summary.get("key_signals"):
            items.append(
                {
                    "scope": "macro",
                    "kind": "macro_shift",
                    "title": "Macro regime update",
                    "summary": " / ".join(macro_summary.get("key_signals", [])[:3]),
                    "why_now": f"{macro_summary.get('environment', 'unknown')} · {macro_summary.get('risk_level', 'unknown')} risk",
                    "symbols": [],
                    "primary_symbol": None,
                    "confidence": 0.72,
                    "impact_score": 0.7,
                    "horizon": "short",
                    "urgency_score": 0.62,
                    "evidence": [
                        {
                            "category": "macro_events",
                            "source": "macro_intelligence",
                            "summary": " / ".join(macro_summary.get("key_signals", [])[:3]),
                            "confidence": 0.72,
                            "score": 0.7,
                        }
                    ],
                }
            )
        fear_greed = macro_context.get("fear_greed") if isinstance(macro_context, dict) else None
        if fear_greed and fear_greed.get("value") is not None:
            items.append(
                {
                    "scope": "macro",
                    "kind": "macro_shift",
                    "title": "Cross-asset sentiment regime",
                    "summary": f"Fear & Greed at {fear_greed.get('value')} ({fear_greed.get('classification')})",
                    "why_now": "Useful for position sizing and short-term aggression.",
                    "symbols": [],
                    "primary_symbol": None,
                    "confidence": 0.64,
                    "impact_score": 0.55,
                    "horizon": "short",
                    "urgency_score": 0.52,
                    "evidence": [
                        {
                            "category": "macro_events",
                            "source": fear_greed.get("source", "alternative.me"),
                            "summary": f"Fear & Greed at {fear_greed.get('value')}",
                            "confidence": 0.64,
                            "score": abs((float(fear_greed.get('value', 50)) - 50) / 50),
                        }
                    ],
                }
            )
        return items

    def _from_research_hooks(self, news_feed: dict) -> list[dict]:
        """Seed research scope even before the standalone research view is opened."""
        if self.holding_symbols or self.watchlist_symbols:
            return []
        for article in news_feed.get("articles", []):
            symbols = article.get("ticker_mentions", [])
            if not symbols:
                continue
            return [
                {
                    "scope": "research",
                    "kind": "opportunity",
                    "title": f"Research candidate: {symbols[0]}",
                    "summary": article.get("headline", "Candidate from market-wide scan"),
                    "why_now": "No portfolio/watchlist loaded, so the inbox is surfacing market-wide opportunities.",
                    "symbols": [symbols[0]],
                    "primary_symbol": symbols[0],
                    "confidence": float(article.get("confidence", 0.0)),
                    "impact_score": 0.5,
                    "horizon": "short",
                    "urgency_score": 0.45,
                    "evidence": [
                        {
                            "category": article.get("source_category", "news"),
                            "source": article.get("source_provider", article.get("source", "news")),
                            "summary": article.get("headline", ""),
                            "url": article.get("url"),
                            "confidence": float(article.get("confidence", 0.0)),
                            "score": abs(float(article.get("sentiment_score", 0.0))),
                        }
                    ],
                }
            ]
        return []

    def _resolve_scope(self, symbol: str | None, kind: str) -> str:
        symbol = (symbol or "").upper()
        if symbol and symbol in self.holding_symbols:
            return "portfolio"
        if symbol and symbol in self.watchlist_symbols:
            return "watchlist"
        if kind in {"macro_shift", "macro", "event"} and not symbol:
            return "macro"
        return "research"

    def _novelty_score(self, candidate: dict) -> float:
        for item in self.previous_items:
            if item.get("kind") == candidate.get("kind") and item.get("primary_symbol") == candidate.get("primary_symbol"):
                return 0.45
        return 0.95

    def _user_fit_score(self, candidate: dict) -> float:
        risk_tolerance = self.profile.get("risk_tolerance", "moderate")
        target_horizon = self.profile.get("default_horizon") or self.profile.get("investment_horizon", "medium")
        horizon_score = 1.0 if candidate.get("horizon") == target_horizon else 0.72
        kind = candidate.get("kind")
        risk_score = 0.6
        if risk_tolerance == "conservative":
            if kind in {"risk_alert", "rebalance", "macro_shift"}:
                risk_score = 0.95
            elif kind in {"social_signal", "trend"}:
                risk_score = 0.45
        elif risk_tolerance == "aggressive":
            if kind in {"opportunity", "trend", "social_signal"}:
                risk_score = 0.92
            elif kind in {"rebalance", "macro_shift"}:
                risk_score = 0.58
        else:
            risk_score = 0.82 if kind in {"opportunity", "risk_alert", "earnings_watch"} else 0.68
        return _clip((horizon_score + risk_score) / 2)

    def _portfolio_impact_score(self, candidate: dict) -> float:
        symbol = candidate.get("primary_symbol")
        if symbol and symbol in self.holding_weights:
            return _clip(0.35 + self.holding_weights[symbol] * 2.4)
        if symbol and symbol in self.watchlist_symbols:
            return 0.55
        if candidate.get("scope") == "portfolio":
            return 0.65
        if candidate.get("scope") == "macro":
            return 0.6 if self.holdings else 0.45
        return 0.38

    def _source_breakdown(self, evidence: list[dict]) -> list[dict]:
        grouped: dict[str, dict] = defaultdict(
            lambda: {"source": "", "count": 0, "weight": 0.0, "confidence": 0.0, "retrieval_mode": "derived"}
        )
        for item in evidence:
            bucket = grouped[item.get("source", "unknown")]
            bucket["source"] = item.get("source", "unknown")
            bucket["count"] += 1
            bucket["weight"] += float(item.get("score", 0.0))
            bucket["confidence"] += float(item.get("confidence", 0.0))
        result = []
        for bucket in grouped.values():
            count = max(bucket["count"], 1)
            result.append(
                {
                    "source": bucket["source"],
                    "count": bucket["count"],
                    "weight": round(bucket["weight"] / count, 4),
                    "confidence": round(bucket["confidence"] / count, 4),
                    "retrieval_mode": bucket["retrieval_mode"],
                }
            )
        return sorted(result, key=lambda item: (-item["weight"], -item["confidence"]))

    def _finalize_items(self, items: list[dict]) -> list[dict]:
        unique: dict[tuple[str, str | None], dict] = {}
        expires_at = _expires_at()
        assistant_mode = self.profile.get("assistant_mode", AssistantMode.BALANCED.value)

        for candidate in items:
            key = (candidate.get("title", ""), candidate.get("primary_symbol"))
            if key in unique:
                unique[key]["evidence"].extend(candidate.get("evidence", []))
                unique[key]["confidence"] = max(unique[key]["confidence"], candidate.get("confidence", 0.0))
                continue
            unique[key] = candidate

        finalized: list[dict] = []
        for candidate in unique.values():
            evidence = candidate.get("evidence", [])
            evidence_categories = {item.get("category", "") for item in evidence}
            non_social_categories = {
                category for category in evidence_categories if category not in {"social"}
            }
            confirmed = len(non_social_categories) >= 2
            social_only = evidence_categories == {"social"} and len(evidence_categories) == 1
            urgency = _clip(float(candidate.get("urgency_score", 0.5)))
            portfolio_impact = self._portfolio_impact_score(candidate)
            confidence = _clip(float(candidate.get("confidence", 0.0)))
            novelty = self._novelty_score(candidate)
            user_fit = self._user_fit_score(candidate)
            priority = (
                urgency * 0.30
                + portfolio_impact * 0.25
                + confidence * 0.20
                + novelty * 0.15
                + user_fit * 0.10
            ) * 100
            if social_only and not any(
                category in {"price_volume", "news", "portfolio_risk", "macro_events"}
                for category in evidence_categories
            ):
                priority = min(priority, 60.0)
            if assistant_mode == AssistantMode.PRUDENT.value and not confirmed:
                priority *= 0.9
            if assistant_mode == AssistantMode.PROACTIVE.value and candidate.get("kind") == "opportunity":
                priority *= 1.05

            created_at = _iso_now()
            finalized.append(
                {
                    "id": str(uuid.uuid4()),
                    "scope": candidate.get("scope", "research"),
                    "kind": candidate.get("kind", "opportunity"),
                    "title": candidate.get("title", "Insight"),
                    "summary": candidate.get("summary", ""),
                    "why_now": candidate.get("why_now", ""),
                    "symbols": candidate.get("symbols", []),
                    "primary_symbol": candidate.get("primary_symbol"),
                    "priority_score": round(priority, 2),
                    "confidence": round(confidence, 4),
                    "impact": _impact_label(float(candidate.get("impact_score", 0.5))),
                    "horizon": candidate.get("horizon", "medium"),
                    "status": "open",
                    "state": "confirmed" if confirmed else "exploratory",
                    "assistant_mode": assistant_mode,
                    "evidence": evidence,
                    "source_breakdown": self._source_breakdown(evidence),
                    "created_at": created_at,
                    "updated_at": created_at,
                    "expires_at": expires_at,
                    "linked_thesis_id": None,
                }
            )

        finalized.sort(
            key=lambda item: (
                0 if item["state"] == "confirmed" else 1,
                -item["priority_score"],
                item["title"],
            )
        )
        return finalized[:20]


def _apply_filters(
    items: list[dict],
    *,
    scope: str | None = None,
    status: str | None = None,
    kind: str | None = None,
    symbol: str | None = None,
) -> list[dict]:
    target_symbol = symbol.upper() if symbol else None
    filtered = []
    for item in items:
        if scope and item.get("scope") != scope:
            continue
        if status:
            state_match = item.get("status") == status or item.get("state") == status
            if not state_match:
                continue
        if kind and item.get("kind") != kind:
            continue
        if target_symbol and target_symbol not in item.get("symbols", []):
            continue
        filtered.append(item)
    return filtered


async def refresh_inbox(user_id: str, tenant_id: str | None = None) -> dict:
    assembler = InsightAssembler(user_id, tenant_id)
    return await assembler.assemble()


async def get_inbox(
    user_id: str,
    tenant_id: str | None = None,
    *,
    scope: str | None = None,
    status: str | None = None,
    kind: str | None = None,
    symbol: str | None = None,
    force_refresh: bool = False,
) -> dict:
    items = store.get_inbox_items(user_id, tenant_id)
    stale = force_refresh
    if items:
        expiry = min(
            [
                parsed
                for parsed in (_parse_iso(item.get("expires_at")) for item in items)
                if parsed is not None
            ],
            default=None,
        )
        stale = stale or expiry is None or expiry <= _utc_now()
    else:
        stale = True

    payload = await refresh_inbox(user_id, tenant_id) if stale else {
        "items": items,
        "generated_at": items[0].get("created_at", _iso_now()) if items else _iso_now(),
        "cached_until": items[0].get("expires_at", _expires_at()) if items else _expires_at(),
    }
    filtered = _apply_filters(
        payload["items"],
        scope=scope,
        status=status,
        kind=kind,
        symbol=symbol,
    )
    return {
        "items": filtered,
        "total": len(filtered),
        "generated_at": payload["generated_at"],
        "cached_until": payload["cached_until"],
    }


def update_inbox_item_state(
    user_id: str,
    item_id: str,
    action: str,
    tenant_id: str | None = None,
    thesis_id: str | None = None,
) -> dict | None:
    item = store.get_inbox_item(user_id, item_id, tenant_id)
    if not item:
        return None
    updates = {"updated_at": _iso_now()}
    if action == "save":
        updates["status"] = "saved"
    elif action == "dismiss":
        updates["status"] = "dismissed"
    elif action == "snooze":
        updates["status"] = "snoozed"
        updates["expires_at"] = _expires_at(3600)
    elif action == "done":
        updates["status"] = "done"
    elif action == "link_thesis":
        updates["status"] = item.get("status", "open")
        updates["linked_thesis_id"] = thesis_id
    else:
        return None
    return store.update_inbox_item(user_id, item_id, updates, tenant_id)


def _item_warnings(item: dict) -> list[str]:
    warnings: list[str] = []
    if item.get("state") != "confirmed":
        warnings.append("Signal is still exploratory and not fully confirmed across categories.")
    if float(item.get("confidence", 0.0) or 0.0) < 0.45:
        warnings.append("Confidence is limited due to thin or conflicting evidence.")
    if len(item.get("source_breakdown", [])) <= 1:
        warnings.append("This insight relies on a narrow source set.")
    return warnings[:3]


def _item_contradictions(item: dict) -> list[str]:
    contradictions: list[str] = []
    evidence_categories = {entry.get("category") for entry in item.get("evidence", [])}
    if "social" in evidence_categories and "technical" not in evidence_categories and "news" not in evidence_categories:
        contradictions.append("Social flow is present without confirmation from technical or news evidence.")
    if item.get("state") != "confirmed":
        contradictions.append("Supporting signals do not fully align yet.")
    return contradictions[:3]


def _item_sources(item: dict) -> list[str]:
    return [bucket.get("source", "unknown") for bucket in item.get("source_breakdown", [])[:5]]


async def build_recommendations_from_inbox(
    user_id: str, tenant_id: str | None = None
) -> dict:
    payload = await get_inbox(user_id, tenant_id)
    items = payload["items"][:6]
    mood_score = 0.0
    if items:
        signed_scores = [
            (1 if item["kind"] in {"opportunity", "trend", "earnings_watch"} else -1)
            * (item["priority_score"] / 100)
            for item in items
        ]
        mood_score = sum(signed_scores) / max(len(signed_scores), 1)
        mood_score = max(-1.0, min(1.0, mood_score))

    top_titles = ", ".join(item["title"] for item in items[:3]) or "No high-priority insights yet."
    recommendations = []
    for item in items:
        recommendations.append(
            {
                "category": item["kind"] if item["kind"] in {
                    "opportunity",
                    "risk_alert",
                    "rebalance",
                    "trend",
                    "macro_shift",
                    "social_signal",
                    "earnings_watch",
                    "sector_rotation",
                } else "opportunity",
                "title": item["title"],
                "reasoning": item["summary"],
                "confidence": item["confidence"],
                "tickers": item["symbols"],
                "action": item["why_now"],
                "urgency": (
                    "high"
                    if item["priority_score"] >= 75
                    else "medium" if item["priority_score"] >= 50 else "low"
                ),
                "inbox_item_id": item["id"],
                "why_now": item["why_now"],
                "horizon": item["horizon"],
                "sources": _item_sources(item),
                "warnings": _item_warnings(item),
                "contradictions": _item_contradictions(item),
            }
        )

    return {
        "market_mood": top_titles,
        "mood_score": round(mood_score, 4),
        "recommendations": recommendations,
        "sources": sorted({source for item in items for source in _item_sources(item)}),
        "warnings": [warning for item in items[:3] for warning in _item_warnings(item)][:6],
        "contradictions": [warning for item in items[:3] for warning in _item_contradictions(item)][:6],
        "generated_at": payload["generated_at"],
    }


async def build_briefing_from_inbox(
    user_id: str,
    tenant_id: str | None = None,
    *,
    preset: str = "default",
) -> dict:
    payload = await get_inbox(user_id, tenant_id)
    items = payload["items"]
    top_items = items[:3]
    summary_lines = [
        "## Daily Decision Brief",
        *(f"- {item['title']}: {item['why_now'] or item['summary']}" for item in top_items),
    ]
    if not top_items:
        summary_lines.append("- No priority items yet. The system is waiting for new catalysts.")

    event_titles = [
        item["title"]
        for item in items
        if item["kind"] in {"earnings_watch", "macro_shift", "filing", "insider"}
    ][:3]
    suggestions = [f"Open {item['primary_symbol'] or item['scope']}" for item in top_items[:4]]
    if not suggestions:
        suggestions = ["Review macro regime", "Refresh inbox"]

    from app.services.event_engine import build_events  # local import for consistency
    from app.services.economic_calendar import fetch_economic_calendar

    calendar = await fetch_economic_calendar()
    symbols = [
        holding["symbol"].upper()
        for holding in store.get_holdings(user_id, tenant_id)
    ]
    if not symbols:
        for watchlist in store.get_watchlists(user_id, tenant_id):
            for asset in watchlist.get("assets", []):
                symbols.append(asset["symbol"].upper())
    events = build_events(
        symbols=symbols,
        calendar=calendar,
    )
    theses = store.get_theses(user_id, tenant_id)[:3]

    if event_titles:
        summary_lines.append("")
        summary_lines.append("## Next Catalysts")
        summary_lines.extend(f"- {title}" for title in event_titles)

    return {
        "briefing": "\n".join(summary_lines),
        "suggestions": suggestions,
        "generated_at": payload["generated_at"],
        "preset": preset,
        "top_inbox_items": top_items,
        "next_events": events[:5],
        "thesis_watch": theses,
        "sources": sorted({source for item in top_items for source in _item_sources(item)}),
        "warnings": [warning for item in top_items for warning in _item_warnings(item)][:6],
        "contradictions": [warning for item in top_items for warning in _item_contradictions(item)][:6],
    }
