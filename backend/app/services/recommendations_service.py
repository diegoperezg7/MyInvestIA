"""AI recommendations engine.

Gathers portfolio, watchlist, quotes, macro, news, social sentiment,
signals, and alerts in parallel, then synthesizes actionable recommendations
using Mistral AI.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from app.services.ai_service import ai_service
from app.services.cache import get_or_fetch
from app.services.macro_intelligence import get_all_macro_indicators, get_macro_summary
from app.services.market_data import market_data_service
from app.services.news_service import news_service
from app.services.store import store

logger = logging.getLogger(__name__)

RECOMMENDATIONS_TTL = 900  # 15 minutes

RECOMMENDATIONS_SYSTEM_PROMPT = """You are InvestIA, an AI investment intelligence engine. Your job is to synthesize market data, technical signals, macro indicators, news, and social sentiment into actionable recommendations.

You MUST respond with ONLY valid JSON (no markdown, no explanation). The JSON must have this structure:
{
  "market_mood": "2-sentence executive summary of current market conditions",
  "mood_score": float between -1.0 (very bearish) and 1.0 (very bullish),
  "recommendations": [
    {
      "category": "opportunity|risk_alert|rebalance|trend|macro_shift|social_signal|earnings_watch|sector_rotation",
      "title": "Short title in Spanish",
      "reasoning": "2-3 sentences explaining WHY, in Spanish",
      "confidence": float 0.0-1.0,
      "tickers": ["SYM1", "SYM2"],
      "action": "What to do (in Spanish)",
      "urgency": "low|medium|high"
    }
  ]
}

Categories:
- opportunity: Detected opportunity (bullish technicals + positive sentiment)
- risk_alert: Risk warning (adverse macro or technical indicators)
- rebalance: Rebalancing suggestion (excessive concentration, extreme P&L)
- trend: Detected trend (moving averages, momentum)
- macro_shift: Macro change (VIX, yields, commodities)
- social_signal: Social signal (viral buzz, sentiment divergence)
- earnings_watch: Watch earnings/events
- sector_rotation: Detected sector rotation

Guidelines:
- Generate 5-8 recommendations
- ALL text (titles, reasoning, actions) must be in SPANISH
- Use actual data: prices, percentages, indicators
- Be specific and actionable
- Never give financial advice — provide analysis and decision support only
- Each recommendation should reference specific data points"""


async def generate_recommendations() -> dict:
    """Generate AI-powered investment recommendations."""

    async def _fetch():
        # Collect symbols
        holdings = store.get_holdings()
        watchlists = store.get_watchlists()

        holding_symbols = [h["symbol"] for h in holdings]
        watchlist_symbols: list[str] = []
        for wl in watchlists:
            for asset in wl.get("assets", []):
                sym = asset["symbol"]
                if sym not in holding_symbols and sym not in watchlist_symbols:
                    watchlist_symbols.append(sym)

        all_symbols = holding_symbols + watchlist_symbols

        # Parallel data gathering
        quote_items = [{"symbol": s} for s in all_symbols] if all_symbols else []

        tasks: dict[str, asyncio.Task] = {}
        async with asyncio.TaskGroup() as tg:
            if quote_items:
                tasks["quotes"] = tg.create_task(
                    market_data_service.get_quotes(quote_items)
                )
            tasks["macro"] = tg.create_task(get_all_macro_indicators())
            tasks["market_news"] = tg.create_task(news_service.get_market_news(limit=10))
            if all_symbols:
                tasks["portfolio_news"] = tg.create_task(
                    news_service.get_portfolio_news(all_symbols, limit_per_symbol=3)
                )
                tasks["social"] = tg.create_task(
                    news_service.get_portfolio_social_sentiment(all_symbols)
                )

        quotes = tasks["quotes"].result() if "quotes" in tasks else []
        macro_indicators = tasks["macro"].result()
        macro_summary = get_macro_summary(macro_indicators)
        market_news = tasks["market_news"].result()
        portfolio_news = tasks["portfolio_news"].result() if "portfolio_news" in tasks else []
        social_sentiment = tasks["social"].result() if "social" in tasks else []

        # Build signals for top holdings
        signal_summaries = await _get_signal_summaries(holding_symbols[:5])

        # Build context
        context = _build_recommendations_context(
            holdings=holdings,
            watchlist_symbols=watchlist_symbols,
            quotes=quotes,
            macro_indicators=macro_indicators,
            macro_summary=macro_summary,
            market_news=market_news,
            portfolio_news=portfolio_news,
            social_sentiment=social_sentiment,
            signal_summaries=signal_summaries,
        )

        # Generate with AI
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        user_prompt = (
            f"Current time: {now}. Based on ALL the data below, generate investment recommendations.\n\n"
            f"{context}"
        )

        if ai_service.is_configured:
            try:
                response = await ai_service.chat(
                    messages=[{"role": "user", "content": user_prompt}],
                    max_tokens=2000,
                    model="mistral-large-latest",
                    system_override=RECOMMENDATIONS_SYSTEM_PROMPT,
                )
                result = _parse_ai_response(response)
                if result:
                    result["generated_at"] = datetime.now(timezone.utc).isoformat()
                    return result
            except Exception as e:
                logger.warning("AI recommendations failed: %s", e)

        # Fallback
        return _fallback_recommendations(
            holdings, quotes, macro_indicators, macro_summary
        )

    return await get_or_fetch("recommendations:latest", _fetch, RECOMMENDATIONS_TTL) or {
        "market_mood": "No se pudieron generar recomendaciones en este momento.",
        "mood_score": 0.0,
        "recommendations": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def _get_signal_summaries(symbols: list[str]) -> list[dict]:
    """Get signal summaries for symbols, silently failing."""
    if not symbols:
        return []
    try:
        from app.services.signal_aggregator import build_signal_summary
        from app.services.technical_analysis import compute_all_indicators

        results = []
        for sym in symbols:
            try:
                history = await market_data_service.get_history(sym, period="6mo", interval="1d")
                if history and len(history) >= 30:
                    closes = [r["close"] for r in history]
                    indicators = compute_all_indicators(closes)
                    summary = build_signal_summary(sym, indicators, closes[-1])
                    results.append({
                        "symbol": sym,
                        "overall": summary.overall.value,
                        "confidence": summary.overall_confidence,
                        "oscillators": summary.oscillators_rating.value,
                        "moving_averages": summary.moving_averages_rating.value,
                    })
            except Exception:
                pass
        return results
    except Exception:
        return []


def _build_recommendations_context(
    holdings: list[dict],
    watchlist_symbols: list[str],
    quotes: list[dict],
    macro_indicators: list[dict],
    macro_summary: dict,
    market_news: list[dict],
    portfolio_news: list[dict],
    social_sentiment: list[dict],
    signal_summaries: list[dict],
) -> str:
    """Build rich context for AI recommendations."""
    parts: list[str] = []

    # Portfolio
    if holdings:
        lines = ["## Portfolio Holdings"]
        total_value = 0.0
        for h in holdings:
            sym = h["symbol"]
            qty = h["quantity"]
            avg = h["avg_buy_price"]
            quote = next((q for q in quotes if q.get("symbol") == sym), None)
            if quote:
                price = quote.get("price", 0)
                change = quote.get("change_percent", 0)
                pnl = (price - avg) * qty
                value = price * qty
                total_value += value
                lines.append(
                    f"- {sym}: {qty} shares @ ${avg:.2f} avg | "
                    f"Now ${price:.2f} ({change:+.2f}%) | P&L: ${pnl:+,.2f} | Value: ${value:,.2f}"
                )
            else:
                lines.append(f"- {sym}: {qty} shares @ ${avg:.2f} avg")
        if total_value > 0:
            lines.append(f"\nTotal portfolio value: ${total_value:,.2f}")
            # Concentration check
            for h in holdings:
                sym = h["symbol"]
                quote = next((q for q in quotes if q.get("symbol") == sym), None)
                if quote:
                    value = quote.get("price", 0) * h["quantity"]
                    pct = (value / total_value) * 100 if total_value > 0 else 0
                    if pct > 25:
                        lines.append(f"  ⚠ {sym} concentration: {pct:.1f}% of portfolio")
        parts.append("\n".join(lines))

    # Watchlist
    if watchlist_symbols:
        lines = ["## Watchlist"]
        for sym in watchlist_symbols:
            quote = next((q for q in quotes if q.get("symbol") == sym), None)
            if quote:
                lines.append(f"- {sym}: ${quote.get('price', 0):.2f} ({quote.get('change_percent', 0):+.2f}%)")
        parts.append("\n".join(lines))

    # Signal summaries
    if signal_summaries:
        lines = ["## Technical Signals"]
        for sig in signal_summaries:
            lines.append(
                f"- {sig['symbol']}: {sig['overall']} (confidence: {sig['confidence']:.0f}%) | "
                f"Oscillators: {sig['oscillators']} | MAs: {sig['moving_averages']}"
            )
        parts.append("\n".join(lines))

    # Social sentiment
    if social_sentiment:
        lines = ["## Social Sentiment (24h)"]
        sorted_social = sorted(social_sentiment, key=lambda s: s.get("total_mentions", 0), reverse=True)
        for s in sorted_social:
            sym = s["symbol"]
            lines.append(
                f"- {sym}: {s.get('total_mentions', 0)} mentions | "
                f"Buzz: {s.get('buzz_level', 'none')} | "
                f"Sentiment: {s.get('sentiment_label', 'neutral')} ({s.get('combined_score', 0):+.2f})"
            )
        parts.append("\n".join(lines))

    # Macro
    if macro_indicators:
        lines = ["## Macro Indicators"]
        for ind in macro_indicators:
            lines.append(
                f"- {ind['name']}: {ind['value']:.2f} ({ind['change_percent']:+.2f}%) — {ind['impact_description']}"
            )
        if macro_summary.get("key_signals"):
            lines.append(f"\nEnvironment: {macro_summary.get('environment', 'unknown')}, "
                         f"Risk: {macro_summary.get('risk_level', 'unknown')}")
            for signal in macro_summary.get("key_signals", []):
                lines.append(f"  - {signal}")
        parts.append("\n".join(lines))

    # Market news
    if market_news:
        lines = ["## Market News"]
        for article in market_news[:8]:
            lines.append(f"- [{article.get('source', '')}] {article.get('headline', '')}")
        parts.append("\n".join(lines))

    # Portfolio news
    if portfolio_news:
        lines = ["## Company News"]
        for article in portfolio_news[:8]:
            lines.append(f"- [{article.get('related', '')}] {article.get('headline', '')}")
        parts.append("\n".join(lines))

    if not parts:
        parts.append("No portfolio or watchlist data. Provide general market recommendations.")

    return "\n\n".join(parts)


def _parse_ai_response(response: str) -> dict | None:
    """Parse AI JSON response into recommendations dict."""
    try:
        text = response.strip()
        # Remove markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        data = json.loads(text)
        if not isinstance(data, dict):
            return None

        # Validate required fields
        market_mood = str(data.get("market_mood", ""))
        mood_score = float(data.get("mood_score", 0.0))
        mood_score = max(-1.0, min(1.0, mood_score))

        recommendations = []
        valid_categories = {
            "opportunity", "risk_alert", "rebalance", "trend",
            "macro_shift", "social_signal", "earnings_watch", "sector_rotation",
        }
        valid_urgencies = {"low", "medium", "high"}

        for rec in data.get("recommendations", []):
            if not isinstance(rec, dict):
                continue
            category = rec.get("category", "")
            if category not in valid_categories:
                continue
            recommendations.append({
                "category": category,
                "title": str(rec.get("title", ""))[:200],
                "reasoning": str(rec.get("reasoning", ""))[:500],
                "confidence": max(0.0, min(1.0, float(rec.get("confidence", 0.5)))),
                "tickers": [str(t).upper() for t in rec.get("tickers", []) if isinstance(t, str)][:10],
                "action": str(rec.get("action", ""))[:200],
                "urgency": rec.get("urgency", "medium") if rec.get("urgency") in valid_urgencies else "medium",
            })

        if not market_mood and not recommendations:
            return None

        return {
            "market_mood": market_mood,
            "mood_score": mood_score,
            "recommendations": recommendations,
        }
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning("Failed to parse AI recommendations: %s", e)
        return None


def _fallback_recommendations(
    holdings: list[dict],
    quotes: list[dict],
    macro_indicators: list[dict],
    macro_summary: dict,
) -> dict:
    """Generate basic recommendations without AI."""
    recommendations = []

    # Check macro environment
    env = macro_summary.get("environment", "unknown")
    risk = macro_summary.get("risk_level", "unknown")

    if risk in ("high", "elevated"):
        recommendations.append({
            "category": "macro_shift",
            "title": "Entorno de riesgo elevado detectado",
            "reasoning": f"El entorno macro es '{env}' con nivel de riesgo '{risk}'. Considere revisar la exposición al riesgo de su portafolio.",
            "confidence": 0.6,
            "tickers": [],
            "action": "Revisar posiciones y considerar coberturas",
            "urgency": "high",
        })

    # Check for big movers
    if quotes:
        movers = sorted(quotes, key=lambda q: abs(q.get("change_percent", 0)), reverse=True)
        for q in movers[:3]:
            change = q.get("change_percent", 0)
            if abs(change) >= 3:
                sym = q["symbol"]
                if change > 0:
                    recommendations.append({
                        "category": "trend",
                        "title": f"{sym} con movimiento alcista significativo",
                        "reasoning": f"{sym} sube {change:+.2f}% hoy. Evalúe si el momentum continúa.",
                        "confidence": 0.5,
                        "tickers": [sym],
                        "action": "Monitorear y evaluar señales técnicas",
                        "urgency": "medium",
                    })
                else:
                    recommendations.append({
                        "category": "risk_alert",
                        "title": f"{sym} con caída notable",
                        "reasoning": f"{sym} baja {change:+.2f}% hoy. Evalúe si mantener o reducir posición.",
                        "confidence": 0.5,
                        "tickers": [sym],
                        "action": "Analizar causa y revisar stop-loss",
                        "urgency": "medium",
                    })

    return {
        "market_mood": f"Entorno de mercado: {env}. Nivel de riesgo: {risk}. (Recomendaciones básicas — IA no disponible.)",
        "mood_score": 0.0,
        "recommendations": recommendations[:8],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
