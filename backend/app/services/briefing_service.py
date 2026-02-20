"""AI briefing orchestrator.

Gathers portfolio, watchlist, quotes, macro indicators, news, and social
sentiment (Reddit + Twitter) in parallel, then asks the AI to generate a
proactive briefing with suggestion chips.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone

from app.services.ai_service import ai_service
from app.services.cache import get_or_fetch
from app.services.macro_intelligence import get_all_macro_indicators, get_macro_summary
from app.services.market_data import market_data_service
from app.services.news_service import news_service
from app.services.store import store

logger = logging.getLogger(__name__)

BRIEFING_TTL = 300  # 5 minutes

BRIEFING_SYSTEM_PROMPT = """You are InvestIA, an AI investment intelligence assistant delivering a proactive market briefing.

You have real-time data about the user's portfolio, watchlist, market news, macro indicators, and social media sentiment (Reddit + Twitter). Your job is to synthesize everything into a concise, actionable briefing.

Guidelines:
- Lead with the most important insight (biggest mover, critical news, social buzz spike, or macro shift)
- Use actual numbers: prices, percentages, ticker symbols, mention counts
- Be concise but specific — no filler text
- Cover: portfolio highlights, notable market moves, relevant news, social sentiment signals, macro context
- When social buzz is high or viral for a symbol, highlight it prominently — it often precedes price moves
- If a symbol has conflicting signals (e.g. bearish technicals but bullish social buzz), flag the divergence
- If the user has no portfolio/watchlist, focus on market-wide insights
- End with exactly 3-5 suggestion chips in [brackets] on separate lines
- Suggestions should be specific and actionable, like: [Analyze AAPL earnings impact], [Check NVDA social buzz], [Review portfolio risk exposure]
- NEVER give financial advice — provide analysis and decision support only
- Use markdown formatting for readability"""


def _extract_suggestions(text: str) -> list[str]:
    """Extract [bracketed] suggestion chips from AI response."""
    return re.findall(r"\[([^\]]+)\]", text)


def _build_context(
    holdings: list[dict],
    watchlist_symbols: list[str],
    quotes: list[dict],
    macro_indicators: list[dict],
    macro_summary: dict,
    market_news: list[dict],
    portfolio_news: list[dict],
    social_sentiment: list[dict] | None = None,
) -> str:
    """Build a rich text context string from all data sources."""
    parts: list[str] = []

    # Portfolio holdings
    if holdings:
        lines = ["## Portfolio Holdings"]
        for h in holdings:
            sym = h["symbol"]
            qty = h["quantity"]
            avg = h["avg_buy_price"]
            # Find matching quote
            quote = next((q for q in quotes if q.get("symbol") == sym), None)
            if quote:
                price = quote.get("price", 0)
                change = quote.get("change_percent", 0)
                pnl = (price - avg) * qty
                lines.append(
                    f"- {sym}: {qty} shares @ ${avg:.2f} avg | "
                    f"Now ${price:.2f} ({change:+.2f}%) | P&L: ${pnl:+,.2f}"
                )
            else:
                lines.append(f"- {sym}: {qty} shares @ ${avg:.2f} avg")
        parts.append("\n".join(lines))

    # Watchlist
    if watchlist_symbols:
        lines = ["## Watchlist"]
        for sym in watchlist_symbols:
            quote = next((q for q in quotes if q.get("symbol") == sym), None)
            if quote:
                price = quote.get("price", 0)
                change = quote.get("change_percent", 0)
                lines.append(f"- {sym}: ${price:.2f} ({change:+.2f}%)")
            else:
                lines.append(f"- {sym}: (no quote available)")
        parts.append("\n".join(lines))

    # Social Sentiment (Reddit + Twitter)
    if social_sentiment:
        lines = ["## Social Media Sentiment (Reddit + Twitter, last 24h)"]
        # Sort by total mentions descending — most buzz first
        sorted_social = sorted(
            social_sentiment, key=lambda s: s.get("total_mentions", 0), reverse=True
        )
        for s in sorted_social:
            sym = s["symbol"]
            buzz = s.get("buzz_level", "none")
            label = s.get("sentiment_label", "neutral")
            mentions = s.get("total_mentions", 0)
            score = s.get("combined_score", 0)
            reddit_m = s.get("reddit", {}).get("mentions", 0)
            twitter_m = s.get("twitter", {}).get("mentions", 0)
            lines.append(
                f"- {sym}: {mentions} mentions (Reddit: {reddit_m}, Twitter: {twitter_m}) | "
                f"Buzz: {buzz} | Sentiment: {label} (score: {score:+.2f})"
            )
        parts.append("\n".join(lines))

    # Macro indicators
    if macro_indicators:
        lines = ["## Macro Indicators"]
        for ind in macro_indicators:
            lines.append(
                f"- {ind['name']}: {ind['value']:.2f} ({ind['change_percent']:+.2f}%) — {ind['impact_description']}"
            )
        if macro_summary.get("key_signals"):
            lines.append(f"Environment: {macro_summary.get('environment', 'unknown')}, "
                        f"Risk: {macro_summary.get('risk_level', 'unknown')}")
        parts.append("\n".join(lines))

    # Market news
    if market_news:
        lines = ["## Market News"]
        for article in market_news[:8]:
            source = article.get("source", "")
            headline = article.get("headline", "")
            lines.append(f"- [{source}] {headline}")
        parts.append("\n".join(lines))

    # Portfolio/company news
    if portfolio_news:
        lines = ["## Company News (Portfolio & Watchlist)"]
        for article in portfolio_news[:10]:
            related = article.get("related", "")
            headline = article.get("headline", "")
            lines.append(f"- [{related}] {headline}")
        parts.append("\n".join(lines))

    if not parts:
        parts.append("No portfolio or watchlist data available. Provide a general market overview.")

    return "\n\n".join(parts)


async def generate_briefing(user_id: str) -> dict:
    """Generate a proactive AI briefing with suggestion chips.

    Gathers all data in parallel, sends to AI, returns cached result.
    """

    async def _fetch():
        # Collect all symbols from portfolio + watchlists
        holdings = store.get_holdings(user_id)
        watchlists = store.get_watchlists(user_id)

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
            tasks["market_news"] = tg.create_task(news_service.get_market_news(limit=8))
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

        context = _build_context(
            holdings=holdings,
            watchlist_symbols=watchlist_symbols,
            quotes=quotes,
            macro_indicators=macro_indicators,
            macro_summary=macro_summary,
            market_news=market_news,
            portfolio_news=portfolio_news,
            social_sentiment=social_sentiment,
        )

        # Generate AI briefing
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        user_prompt = (
            f"It's {now}. Generate a proactive market briefing based on the data below. "
            "Synthesize the most important insights and end with 3-5 suggestion chips in [brackets]."
        )

        if ai_service.is_configured:
            try:
                briefing_text = await ai_service.chat(
                    messages=[{"role": "user", "content": user_prompt}],
                    context=context,
                    max_tokens=1200,
                    system_override=BRIEFING_SYSTEM_PROMPT,
                )
            except Exception as e:
                logger.warning("AI briefing generation failed: %s", e)
                briefing_text = _fallback_briefing(
                    holdings, quotes, macro_indicators, market_news
                )
        else:
            briefing_text = _fallback_briefing(
                holdings, quotes, macro_indicators, market_news
            )

        suggestions = _extract_suggestions(briefing_text)
        if not suggestions:
            suggestions = _default_suggestions(holding_symbols, watchlist_symbols)

        return {
            "briefing": briefing_text,
            "suggestions": suggestions,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    return await get_or_fetch("briefing:latest", _fetch, BRIEFING_TTL) or {
        "briefing": "Unable to generate briefing at this time.",
        "suggestions": ["Show market overview", "Check macro indicators"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _fallback_briefing(
    holdings: list[dict],
    quotes: list[dict],
    macro_indicators: list[dict],
    market_news: list[dict],
) -> str:
    """Generate a simple text briefing without AI."""
    parts = ["**Market Briefing** (AI unavailable — showing raw data)\n"]

    if quotes:
        movers = sorted(quotes, key=lambda q: abs(q.get("change_percent", 0)), reverse=True)
        parts.append("**Top movers in your portfolio/watchlist:**")
        for q in movers[:5]:
            parts.append(f"- {q['symbol']}: ${q.get('price', 0):.2f} ({q.get('change_percent', 0):+.2f}%)")

    if macro_indicators:
        parts.append("\n**Macro indicators:**")
        for ind in macro_indicators[:4]:
            parts.append(f"- {ind['name']}: {ind['value']:.2f} ({ind['change_percent']:+.2f}%)")

    if market_news:
        parts.append("\n**Recent headlines:**")
        for article in market_news[:5]:
            parts.append(f"- {article.get('headline', '')}")

    if holdings:
        syms = [h["symbol"] for h in holdings[:3]]
        parts.append(f"\n[Analyze {syms[0]}]" if syms else "")
        parts.append("[Review portfolio risk exposure]")
        parts.append("[Check macro indicators]")

    return "\n".join(parts)


def _default_suggestions(
    holding_symbols: list[str], watchlist_symbols: list[str]
) -> list[str]:
    """Generate default suggestion chips when AI doesn't provide them."""
    suggestions = []
    if holding_symbols:
        suggestions.append(f"Analyze {holding_symbols[0]}")
    if len(holding_symbols) > 1:
        suggestions.append(f"Compare {holding_symbols[0]} vs {holding_symbols[1]}")
    if watchlist_symbols:
        suggestions.append(f"Check {watchlist_symbols[0]} signals")
    suggestions.append("Review portfolio risk exposure")
    suggestions.append("Show macro indicators")
    return suggestions[:5]
