"""AI Agent orchestration framework.

Implements the 6 PRD agents as lightweight classes that wrap existing services,
plus a scheduler that runs them periodically in the background. Agents generate
alerts which are persisted to the store and optionally sent via notifications.

Agents:
  1. MarketWatcherAgent — price anomalies, volatility spikes
  2. TechnicalAgent — indicator extremes, multi-factor convergence
  3. SentimentAgent — sentiment shifts, social buzz
  4. MacroAgent — macro risk changes
  5. PortfolioAgent — concentration risk, drawdown
  6. DecisionSynthesizerAgent — fuses all signals into daily briefing
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.schemas.asset import (
    Alert,
    AlertSeverity,
    AlertType,
    SuggestedAction,
)

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_alert(
    alert_type: AlertType,
    severity: AlertSeverity,
    title: str,
    description: str,
    reasoning: str,
    confidence: float,
    action: SuggestedAction,
    symbol: str | None = None,
    agent: str = "",
) -> Alert:
    return Alert(
        id=str(uuid.uuid4()),
        type=alert_type,
        severity=severity,
        title=title,
        description=description,
        reasoning=reasoning,
        confidence=round(min(max(confidence, 0.0), 1.0), 2),
        suggested_action=action,
        created_at=_now_iso(),
        asset_symbol=symbol,
    )


# ---------------------------------------------------------------------------
# Agent base
# ---------------------------------------------------------------------------


class BaseAgent:
    name: str = "base"

    async def run(self, context: dict) -> list[Alert]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# 1. Market Watcher Agent
# ---------------------------------------------------------------------------


class MarketWatcherAgent(BaseAgent):
    """Detects price movements, volume spikes, and volatility anomalies."""

    name = "market_watcher"

    async def run(self, context: dict) -> list[Alert]:
        from app.services.market_data import market_data_service

        alerts: list[Alert] = []
        symbols = context.get("symbols", [])

        sem = asyncio.Semaphore(5)

        async def _check(item: dict) -> list[Alert]:
            async with sem:
                sym = item["symbol"]
                sub: list[Alert] = []
                try:
                    quote = await market_data_service.get_quote(sym, item.get("type"))
                    if not quote:
                        return sub
                    chg = quote.get("change_percent", 0.0)
                    vol = quote.get("volume", 0)

                    # Price spike / drop
                    if abs(chg) >= 5.0:
                        direction = "surging" if chg > 0 else "dropping"
                        sev = AlertSeverity.HIGH if abs(chg) >= 8.0 else AlertSeverity.MEDIUM
                        sub.append(_make_alert(
                            AlertType.PRICE, sev,
                            f"{sym} {direction} {chg:+.1f}%",
                            f"{sym} moved {chg:+.1f}% today.",
                            f"Large single-day move exceeds 5% threshold. May indicate a catalyst.",
                            min(0.5 + abs(chg) / 20.0, 0.9),
                            SuggestedAction.MONITOR, sym, self.name,
                        ))
                except Exception as e:
                    logger.debug("MarketWatcher skip %s: %s", sym, e)
                return sub

        results = await asyncio.gather(*[_check(s) for s in symbols], return_exceptions=True)
        for r in results:
            if isinstance(r, list):
                alerts.extend(r)
        return alerts


# ---------------------------------------------------------------------------
# 2. Technical Agent
# ---------------------------------------------------------------------------


class TechnicalAgent(BaseAgent):
    """Computes indicators and generates technical alerts."""

    name = "technical"

    async def run(self, context: dict) -> list[Alert]:
        from app.services.alert_scorer import scan_symbols

        symbols = context.get("symbols", [])
        if not symbols:
            return []
        # Reuse the existing alert scorer which already does RSI/MACD/multi-factor
        return await scan_symbols(symbols)


# ---------------------------------------------------------------------------
# 3. Sentiment Agent
# ---------------------------------------------------------------------------


class SentimentAgent(BaseAgent):
    """Analyzes sentiment shifts from news and social media."""

    name = "sentiment"

    async def run(self, context: dict) -> list[Alert]:
        alerts: list[Alert] = []
        symbols = context.get("symbols", [])

        sem = asyncio.Semaphore(3)

        async def _check(item: dict) -> list[Alert]:
            async with sem:
                sym = item["symbol"]
                sub: list[Alert] = []
                try:
                    from app.services.enhanced_sentiment_service import get_enhanced_sentiment
                    data = await get_enhanced_sentiment(sym)
                    score = data.get("unified_score", 0.0)
                    label = data.get("unified_label", "neutral")

                    if score >= 0.6:
                        sub.append(_make_alert(
                            AlertType.SENTIMENT, AlertSeverity.MEDIUM,
                            f"{sym} strong bullish sentiment ({score:+.2f})",
                            f"Multi-source sentiment for {sym} is strongly bullish.",
                            f"Unified score {score:.2f} from {data.get('total_data_points', 0)} data points.",
                            0.6, SuggestedAction.MONITOR, sym, self.name,
                        ))
                    elif score <= -0.6:
                        sub.append(_make_alert(
                            AlertType.SENTIMENT, AlertSeverity.MEDIUM,
                            f"{sym} strong bearish sentiment ({score:+.2f})",
                            f"Multi-source sentiment for {sym} is strongly bearish.",
                            f"Unified score {score:.2f} from {data.get('total_data_points', 0)} data points.",
                            0.6, SuggestedAction.MONITOR, sym, self.name,
                        ))
                except Exception as e:
                    logger.debug("SentimentAgent skip %s: %s", sym, e)
                return sub

        results = await asyncio.gather(*[_check(s) for s in symbols[:10]], return_exceptions=True)
        for r in results:
            if isinstance(r, list):
                alerts.extend(r)
        return alerts


# ---------------------------------------------------------------------------
# 4. Macro Agent
# ---------------------------------------------------------------------------


class MacroAgent(BaseAgent):
    """Assesses macroeconomic context and systemic risks."""

    name = "macro"

    async def run(self, context: dict) -> list[Alert]:
        from app.services.macro_intelligence import get_all_macro_indicators, get_macro_summary

        alerts: list[Alert] = []
        try:
            indicators = await get_all_macro_indicators()
            summary = get_macro_summary(indicators)

            risk = summary.get("risk_level", "moderate")
            if risk in ("high", "elevated"):
                alerts.append(_make_alert(
                    AlertType.MACRO, AlertSeverity.HIGH,
                    f"Macro risk level: {risk}",
                    f"Macro environment is {summary.get('environment', 'uncertain')} with {risk} risk.",
                    "; ".join(summary.get("key_signals", [])),
                    0.7, SuggestedAction.MONITOR, agent=self.name,
                ))

            # VIX spike
            for ind in indicators:
                if ind.get("ticker") == "^VIX" and ind.get("value", 0) > 25:
                    alerts.append(_make_alert(
                        AlertType.MACRO, AlertSeverity.HIGH,
                        f"VIX elevated at {ind['value']:.1f}",
                        "Fear index (VIX) is above 25, indicating heightened market fear.",
                        f"VIX at {ind['value']:.1f} with {ind.get('change_percent', 0):.1f}% change.",
                        0.75, SuggestedAction.MONITOR, agent=self.name,
                    ))
        except Exception as e:
            logger.warning("MacroAgent error: %s", e)
        return alerts


# ---------------------------------------------------------------------------
# 5. Portfolio Agent
# ---------------------------------------------------------------------------


class PortfolioAgent(BaseAgent):
    """Evaluates portfolio exposure and risk."""

    name = "portfolio"

    async def run(self, context: dict) -> list[Alert]:
        from app.services.store import store

        alerts: list[Alert] = []
        user_id = context.get("user_id", "")
        holdings = store.get_holdings(user_id) if user_id else []
        if not holdings:
            return alerts

        try:
            from app.services.portfolio_risk import calculate_portfolio_risk
            from app.services.market_data import market_data_service

            # Build holdings with live prices
            enriched = []
            for h in holdings:
                quote = await market_data_service.get_quote(h["symbol"], h.get("type"))
                price = quote.get("price", h["avg_buy_price"]) if quote else h["avg_buy_price"]
                enriched.append({**h, "current_price": price, "current_value": price * h["quantity"]})

            risk = await calculate_portfolio_risk(enriched)

            # High concentration
            conc = risk.get("concentration", {})
            for alert_msg in conc.get("alerts", []):
                alerts.append(_make_alert(
                    AlertType.MULTI_FACTOR, AlertSeverity.MEDIUM,
                    "Portfolio concentration warning",
                    alert_msg,
                    "Diversification reduces portfolio risk.",
                    0.7, SuggestedAction.MONITOR, agent=self.name,
                ))

            # Max drawdown
            metrics = risk.get("metrics", {})
            dd = metrics.get("max_drawdown", 0)
            if dd < -0.2:
                alerts.append(_make_alert(
                    AlertType.MULTI_FACTOR, AlertSeverity.HIGH,
                    f"Portfolio max drawdown {dd:.0%}",
                    f"Your portfolio's maximum drawdown over the past year is {dd:.1%}.",
                    "A drawdown exceeding 20% suggests elevated historical risk.",
                    0.65, SuggestedAction.MONITOR, agent=self.name,
                ))
        except Exception as e:
            logger.warning("PortfolioAgent error: %s", e)

        return alerts


# ---------------------------------------------------------------------------
# 6. Decision Synthesizer
# ---------------------------------------------------------------------------


class DecisionSynthesizerAgent(BaseAgent):
    """Fuses all agent outputs into a coherent summary."""

    name = "synthesizer"

    async def run(self, context: dict) -> list[Alert]:
        """The synthesizer doesn't generate alerts itself.
        It summarizes what other agents found. Results stored in context."""
        all_alerts: list[Alert] = context.get("all_alerts", [])
        if not all_alerts:
            return []

        high_count = sum(1 for a in all_alerts if a.severity in (AlertSeverity.HIGH, AlertSeverity.CRITICAL))
        if high_count >= 3:
            symbols = list({a.asset_symbol for a in all_alerts if a.asset_symbol})
            return [_make_alert(
                AlertType.MULTI_FACTOR, AlertSeverity.CRITICAL,
                f"Multi-agent alert convergence ({high_count} high-severity)",
                f"{high_count} high/critical alerts detected across {', '.join(symbols[:5]) or 'portfolio'}.",
                "Multiple independent agents flagged significant conditions simultaneously, increasing signal reliability.",
                0.8, SuggestedAction.MONITOR, agent=self.name,
            )]
        return []


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class AgentOrchestrator:
    """Runs all agents and aggregates results."""

    def __init__(self):
        self.agents: list[BaseAgent] = [
            MarketWatcherAgent(),
            TechnicalAgent(),
            SentimentAgent(),
            MacroAgent(),
            PortfolioAgent(),
        ]
        self.synthesizer = DecisionSynthesizerAgent()
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_run: str | None = None
        self._last_alerts: list[Alert] = []

    def _gather_symbols(self, user_id: str) -> list[dict]:
        from app.services.store import store

        symbols: list[dict] = []
        seen: set[str] = set()
        for h in store.get_holdings(user_id):
            sym = h["symbol"]
            if sym not in seen:
                symbols.append({"symbol": sym, "type": h.get("type", "stock")})
                seen.add(sym)
        for wl in store.get_watchlists(user_id):
            for a in wl.get("assets", []):
                sym = a["symbol"]
                if sym not in seen:
                    symbols.append({"symbol": sym, "type": a.get("type", "stock")})
                    seen.add(sym)
        return symbols

    async def run_all(self, user_id: str = "") -> list[Alert]:
        """Run all agents once and return combined alerts."""
        if not user_id:
            logger.info("No user_id provided — skipping agent run")
            return []

        symbols = self._gather_symbols(user_id)
        if not symbols:
            logger.info("No symbols to scan — skipping agent run")
            return []

        context = {"symbols": symbols, "user_id": user_id}
        all_alerts: list[Alert] = []

        # Run agents in parallel
        tasks = [agent.run(context) for agent in self.agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for agent, result in zip(self.agents, results):
            if isinstance(result, list):
                all_alerts.extend(result)
                logger.info("Agent %s produced %d alerts", agent.name, len(result))
            elif isinstance(result, Exception):
                logger.error("Agent %s failed: %s", agent.name, result)

        # Deduplicate by title
        seen_titles: set[str] = set()
        unique: list[Alert] = []
        for a in all_alerts:
            if a.title not in seen_titles:
                seen_titles.add(a.title)
                unique.append(a)

        # Run synthesizer
        context["all_alerts"] = unique
        synth_alerts = await self.synthesizer.run(context)
        unique.extend(synth_alerts)

        # Persist alerts
        self._persist_alerts(user_id, unique)

        self._last_run = _now_iso()
        self._last_alerts = unique

        # Notify high/critical alerts
        await self._notify(unique)

        logger.info("Agent orchestrator: %d total alerts from %d agents", len(unique), len(self.agents))
        return unique

    def _persist_alerts(self, user_id: str, alerts: list[Alert]):
        """Store alerts in memory/store for history."""
        from app.services.store import store
        for alert in alerts:
            store.save_memory(
                user_id=user_id,
                category="alert_history",
                content=alert.title,
                metadata={
                    "alert_id": alert.id,
                    "type": alert.type.value,
                    "severity": alert.severity.value,
                    "symbol": alert.asset_symbol,
                    "confidence": alert.confidence,
                    "action": alert.suggested_action.value,
                    "description": alert.description,
                    "reasoning": alert.reasoning,
                },
            )

    async def _notify(self, alerts: list[Alert]):
        """Send high/critical alerts via configured notification channel."""
        try:
            from app.services.telegram_service import telegram_service
            if not telegram_service.configured:
                return
            for alert in alerts:
                if alert.severity in (AlertSeverity.HIGH, AlertSeverity.CRITICAL):
                    await telegram_service.send_alert({
                        "title": alert.title,
                        "description": alert.description,
                        "severity": alert.severity.value,
                        "asset_symbol": alert.asset_symbol or "",
                        "suggested_action": alert.suggested_action.value,
                        "confidence": alert.confidence,
                    })
        except Exception as e:
            logger.warning("Notification error: %s", e)

    # --- Background scheduler ---

    async def _scheduler_loop(self, interval_minutes: int = 30):
        """Background loop that runs agents periodically."""
        while self._running:
            try:
                logger.info("Scheduled agent run starting...")
                await self.run_all()
            except Exception as e:
                logger.error("Scheduled agent run failed: %s", e)
            await asyncio.sleep(interval_minutes * 60)

    def start_scheduler(self, interval_minutes: int = 30):
        """Start the background scheduler."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop(interval_minutes))
        logger.info("Agent scheduler started (every %d min)", interval_minutes)

    def stop_scheduler(self):
        """Stop the background scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Agent scheduler stopped")

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "last_run": self._last_run,
            "agents": [a.name for a in self.agents] + [self.synthesizer.name],
            "last_alert_count": len(self._last_alerts),
        }


# Singleton
orchestrator = AgentOrchestrator()
