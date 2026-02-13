"""All-in-one prediction service.

Gathers every available data source in parallel and synthesizes a unified
prediction using mistral-large-latest.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from app.services.ai_service import ai_service
from app.services.cache import get_or_fetch
from app.services.quant_scoring import compute_quant_scores

logger = logging.getLogger(__name__)

PREDICTION_TTL = 600  # 10 minutes

PREDICTION_SYSTEM_PROMPT = """You are InvestIA, an expert AI investment analyst. A quantitative scoring engine has already computed a verdict and confidence based on 7 algorithmic factors. Your job is to EXPLAIN and CONTEXTUALIZE the quant scores — NOT to invent your own verdict.

You MUST respond with ONLY valid JSON (no markdown, no extra text). The JSON must follow this exact structure:
{
  "verdict_adjustment": "none|upgrade|downgrade",
  "adjustment_reason": "Only fill if adjustment is not none — explain why sentiment/news justifies shifting the quant verdict by one step",
  "technical_summary": {
    "signal": "bullish|bearish|neutral",
    "key_indicators": ["indicator1: value (signal)", "indicator2: value (signal)"],
    "support": "<nearest support level or 'N/A'>",
    "resistance": "<nearest resistance level or 'N/A'>"
  },
  "sentiment_summary": {
    "unified_score": <float -1.0 to 1.0>,
    "label": "bullish|bearish|neutral",
    "key_factors": ["factor1", "factor2"],
    "divergences": ["any signal conflicts"]
  },
  "macro_summary": {
    "environment": "risk-on|risk-off|neutral",
    "risk_level": "low|moderate|elevated|high",
    "vix_regime": "low_vol|normal|elevated|crisis",
    "impact_on_asset": "1 sentence how macro affects this specific asset"
  },
  "news_summary": {
    "headline_count": <int>,
    "overall_tone": "positive|negative|neutral|mixed",
    "top_headlines": ["headline1", "headline2"],
    "summary": "1 sentence"
  },
  "social_summary": {
    "buzz_level": "none|low|moderate|high|viral",
    "total_mentions": <int>,
    "trend": "rising|falling|stable",
    "summary": "1 sentence"
  },
  "price_outlook": {
    "short_term": "1-2 sentence outlook for next 1-2 weeks",
    "medium_term": "1-2 sentence outlook for next 1-3 months",
    "catalysts": ["catalyst1", "catalyst2"],
    "risks": ["risk1", "risk2"]
  },
  "ai_analysis": "Full 4-6 paragraph narrative analysis IN SPANISH. You MUST reference the quant scores (composite, each factor, regime). Explain WHY the numbers are what they are. Cover: quant verdict explanation, technical picture, sentiment landscape, macro context, and final recommendation. Be specific with numbers and data points."
}

CRITICAL RULES:
- The verdict and confidence come from the QUANT ENGINE — you do NOT set them
- You may suggest a verdict_adjustment of "upgrade" or "downgrade" (shifts verdict by ±1 step) ONLY if news/sentiment data provides a compelling reason that the quant model cannot capture (e.g., breaking news, earnings surprise)
- The ai_analysis MUST be written entirely in SPANISH
- Reference the specific quant factor scores and explain what drives each one
- Be honest about uncertainty and conflicting signals
- Never promise future returns — provide analysis and scenarios"""


async def generate_prediction(symbol: str) -> dict:
    """Generate an all-in-one prediction for a symbol."""
    symbol = symbol.upper()

    async def _fetch():
        # Import here to avoid circular imports
        from app.services.enhanced_sentiment_service import get_enhanced_sentiment
        from app.services.macro_intelligence import get_all_macro_indicators, get_macro_summary
        from app.services.market_data import market_data_service
        from app.services.news_service import news_service
        from app.services.newsapi_service import newsapi_service
        from app.services.rss_service import get_rss_news
        from app.services.signal_aggregator import build_signal_summary
        from app.services.store import store
        from app.services.technical_analysis import compute_all_indicators

        # Parallel data gathering
        tasks: dict[str, asyncio.Task] = {}
        async with asyncio.TaskGroup() as tg:
            tasks["quote"] = tg.create_task(market_data_service.get_quote(symbol))
            tasks["history"] = tg.create_task(
                market_data_service.get_history(symbol, period="6mo", interval="1d")
            )
            tasks["enhanced_sentiment"] = tg.create_task(get_enhanced_sentiment(symbol))
            tasks["social"] = tg.create_task(news_service.get_social_sentiment(symbol))
            tasks["macro"] = tg.create_task(get_all_macro_indicators())
            tasks["newsapi"] = tg.create_task(newsapi_service.get_symbol_news(symbol, limit=10))
            tasks["rss"] = tg.create_task(get_rss_news(limit=30))
            tasks["market_news"] = tg.create_task(news_service.get_market_news(limit=5))

        quote = tasks["quote"].result()
        history = tasks["history"].result()
        enhanced_sentiment = tasks["enhanced_sentiment"].result()
        social = tasks["social"].result()
        macro_indicators = tasks["macro"].result()
        macro_summary = get_macro_summary(macro_indicators)
        newsapi_articles = tasks["newsapi"].result()
        rss_articles = tasks["rss"].result()
        market_news = tasks["market_news"].result()

        # Compute technicals
        technical_data = None
        signal_summary = None
        if history and len(history) >= 30:
            closes = [r["close"] for r in history]
            technical_data = compute_all_indicators(closes)
            try:
                signal_summary = build_signal_summary(symbol, technical_data, closes[-1])
            except Exception:
                pass

        # Compute quantitative scores (with sentiment data)
        quant_scores = compute_quant_scores(
            history or [], macro_indicators, enhanced_sentiment
        )

        # Filter RSS for symbol
        rss_mentions = [
            a for a in rss_articles
            if symbol.lower() in (a.get("headline", "") + " " + a.get("summary", "")).lower()
        ]

        # Collect news headlines
        headlines = []
        for a in newsapi_articles:
            h = a.get("title") or a.get("headline", "")
            if h:
                headlines.append(h.strip())
        for a in rss_mentions:
            h = a.get("headline", "")
            if h:
                headlines.append(h.strip())

        # Portfolio context
        holdings = store.get_holdings()
        portfolio_context = ""
        for h in holdings:
            if h["symbol"] == symbol:
                portfolio_context = (
                    f"User holds {h['quantity']} shares at ${h['avg_buy_price']:.2f} avg cost"
                )
                break

        # Build comprehensive context
        context = _build_prediction_context(
            symbol=symbol,
            quote=quote,
            technical_data=technical_data,
            signal_summary=signal_summary,
            enhanced_sentiment=enhanced_sentiment,
            social=social,
            macro_indicators=macro_indicators,
            macro_summary=macro_summary,
            headlines=headlines,
            market_news=market_news,
            portfolio_context=portfolio_context,
            quant_scores=quant_scores,
        )

        # Generate prediction with AI
        if not ai_service.is_configured:
            return _fallback_prediction(symbol, technical_data, enhanced_sentiment, macro_summary, quant_scores)

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        user_prompt = (
            f"Generate a comprehensive prediction for {symbol}. Current time: {now}.\n\n"
            f"{context}"
        )

        try:
            response = await ai_service.chat(
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=3000,
                model="mistral-large-latest",
                system_override=PREDICTION_SYSTEM_PROMPT,
            )
            result = _parse_prediction_response(response, symbol, quant_scores)
            if result:
                result["generated_at"] = datetime.now(timezone.utc).isoformat()
                return result
        except Exception as e:
            logger.warning("AI prediction for %s failed: %s", symbol, e)

        return _fallback_prediction(symbol, technical_data, enhanced_sentiment, macro_summary, quant_scores)

    return await get_or_fetch(f"prediction:{symbol}", _fetch, PREDICTION_TTL) or {
        "symbol": symbol,
        "verdict": "neutral",
        "confidence": 0.0,
        "technical_summary": {},
        "sentiment_summary": {},
        "macro_summary": {},
        "news_summary": {},
        "social_summary": {},
        "price_outlook": {},
        "ai_analysis": "No se pudo generar la predicción.",
        "quant_scores": {},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _build_prediction_context(
    symbol: str,
    quote: dict | None,
    technical_data: dict | None,
    signal_summary: object | None,
    enhanced_sentiment: dict | None,
    social: dict | None,
    macro_indicators: list[dict],
    macro_summary: dict,
    headlines: list[str],
    market_news: list[dict],
    portfolio_context: str,
    quant_scores: dict | None = None,
) -> str:
    """Build a rich context string for the AI prediction prompt."""
    parts: list[str] = []

    # Quantitative scores (placed first — these are the HARD FACTS)
    if quant_scores and quant_scores.get("composite_score") is not None:
        qs = quant_scores
        factors = qs.get("factors", {})
        risk = qs.get("risk_metrics", {})
        sr = qs.get("support_resistance", {})
        lines = [
            "## QUANTITATIVE SCORING ENGINE (HARD FACTS — base your analysis on these)",
            f"- Composite Score: {qs['composite_score']:+.4f}",
            f"- Quant Verdict: {qs['verdict'].upper()} (confidence: {qs['confidence']:.0%})",
            f"- Regime: {qs['regime']} (ADX: {qs.get('adx', 0):.1f})",
            "",
            "Factor Scores [-1.0 to +1.0]:",
        ]
        weights = qs.get("weights", {})
        for fname, fval in factors.items():
            w = weights.get(fname, 0)
            lines.append(f"  - {fname}: {fval:+.4f} (weight: {w:.0%})")
        lines.append("")
        lines.append("Risk Metrics:")
        lines.append(f"  - Sharpe Ratio (63d): {risk.get('sharpe_ratio', 0):.2f}")
        lines.append(f"  - Max Drawdown (63d): {risk.get('max_drawdown', 0):.2f}%")
        lines.append(f"  - Historical Volatility (20d): {risk.get('historical_volatility', 0):.2f}%")
        if sr:
            lines.append("")
            lines.append(f"Support/Resistance: Pivot={sr.get('pivot', 'N/A')}, "
                         f"S1={sr.get('s1', 'N/A')}, S2={sr.get('s2', 'N/A')}, "
                         f"R1={sr.get('r1', 'N/A')}, R2={sr.get('r2', 'N/A')}")
        patterns = qs.get("candlestick_patterns", [])
        if patterns:
            lines.append(f"Candlestick Patterns: {', '.join(patterns)}")
        parts.append("\n".join(lines))

    # Quote data
    if quote:
        parts.append(
            f"## Current Quote\n"
            f"- Price: ${quote.get('price', 'N/A')}\n"
            f"- Change: {quote.get('change_percent', 0):+.2f}%\n"
            f"- Volume: {quote.get('volume', 'N/A')}\n"
            f"- Previous Close: ${quote.get('previous_close', 'N/A')}\n"
            f"- Market Cap: ${quote.get('market_cap', 'N/A')}"
        )

    # Technicals
    if technical_data:
        rsi = technical_data.get("rsi", {})
        macd = technical_data.get("macd", {})
        sma = technical_data.get("sma", {})
        ema = technical_data.get("ema", {})
        bb = technical_data.get("bollinger_bands", {})
        counts = technical_data.get("signal_counts", {})
        parts.append(
            f"## Technical Analysis\n"
            f"- Overall Signal: {technical_data.get('overall_signal', 'N/A')}\n"
            f"- RSI: {rsi.get('value', 'N/A')} ({rsi.get('signal', 'N/A')})\n"
            f"- MACD: histogram={macd.get('histogram', 'N/A')} ({macd.get('signal', 'N/A')})\n"
            f"- SMA: 20={sma.get('sma_20', 'N/A')}, 50={sma.get('sma_50', 'N/A')} ({sma.get('signal', 'N/A')})\n"
            f"- EMA: 12={ema.get('ema_12', 'N/A')}, 26={ema.get('ema_26', 'N/A')} ({ema.get('signal', 'N/A')})\n"
            f"- Bollinger: upper={bb.get('upper', 'N/A')}, lower={bb.get('lower', 'N/A')} ({bb.get('signal', 'N/A')})\n"
            f"- Signal Counts: Bullish={counts.get('bullish', 0)}, Bearish={counts.get('bearish', 0)}, Neutral={counts.get('neutral', 0)}"
        )

    # Signal summary
    if signal_summary:
        try:
            parts.append(
                f"## Signal Aggregation\n"
                f"- Overall: {signal_summary.overall.value} (confidence: {signal_summary.overall_confidence:.0f}%)\n"
                f"- Oscillators: {signal_summary.oscillators_rating.value} "
                f"(Buy: {signal_summary.oscillators_buy}, Sell: {signal_summary.oscillators_sell})\n"
                f"- Moving Averages: {signal_summary.moving_averages_rating.value} "
                f"(Buy: {signal_summary.moving_averages_buy}, Sell: {signal_summary.moving_averages_sell})"
            )
        except Exception:
            pass

    # Enhanced sentiment
    if enhanced_sentiment:
        parts.append(
            f"## Enhanced Sentiment\n"
            f"- Unified Score: {enhanced_sentiment.get('unified_score', 0):+.4f}\n"
            f"- Label: {enhanced_sentiment.get('unified_label', 'neutral')}\n"
            f"- Data Points: {enhanced_sentiment.get('total_data_points', 0)}"
        )
        for src in enhanced_sentiment.get("sources", []):
            parts.append(
                f"  - {src['source_name']}: {src['score']:+.2f} (weight: {src['weight']})"
            )
        divs = enhanced_sentiment.get("divergences", [])
        if divs:
            parts.append("  - Divergences: " + "; ".join(divs))

    # Social
    if social:
        reddit = social.get("reddit", {})
        twitter = social.get("twitter", {})
        parts.append(
            f"## Social Sentiment (24h)\n"
            f"- Total Mentions: {social.get('total_mentions', 0)}\n"
            f"- Buzz Level: {social.get('buzz_level', 'none')}\n"
            f"- Combined Score: {social.get('combined_score', 0):+.2f}\n"
            f"- Reddit: {reddit.get('mentions', 0)} mentions "
            f"({reddit.get('positive_mentions', 0)}+ / {reddit.get('negative_mentions', 0)}-)\n"
            f"- Twitter: {twitter.get('mentions', 0)} mentions "
            f"({twitter.get('positive_mentions', 0)}+ / {twitter.get('negative_mentions', 0)}-)"
        )

    # Macro
    if macro_indicators:
        lines = ["## Macro Context"]
        vix_val = None
        yield_10y = None
        yield_13w = None
        for ind in macro_indicators:
            lines.append(f"- {ind['name']}: {ind['value']:.2f} ({ind['change_percent']:+.2f}%)")
            if "VIX" in ind["name"]:
                vix_val = ind["value"]
            elif "10-Year" in ind["name"]:
                yield_10y = ind["value"]
            elif "13-Week" in ind["name"] or "T-Bill" in ind["name"]:
                yield_13w = ind["value"]

        if vix_val is not None:
            if vix_val < 15:
                lines.append(f"VIX Regime: LOW VOL ({vix_val:.1f})")
            elif vix_val < 20:
                lines.append(f"VIX Regime: NORMAL ({vix_val:.1f})")
            elif vix_val < 30:
                lines.append(f"VIX Regime: ELEVATED ({vix_val:.1f})")
            else:
                lines.append(f"VIX Regime: CRISIS ({vix_val:.1f})")

        if yield_10y is not None and yield_13w is not None:
            spread = yield_10y - yield_13w
            status = "INVERTED" if spread < 0 else "FLAT" if spread < 0.5 else "NORMAL"
            lines.append(f"Yield Curve: {status} (10Y={yield_10y:.2f}%, 13W={yield_13w:.2f}%, spread={spread:+.2f}%)")

        lines.append(f"Environment: {macro_summary.get('environment', 'unknown')}, Risk: {macro_summary.get('risk_level', 'unknown')}")
        parts.append("\n".join(lines))

    # News headlines
    if headlines:
        lines = [f"## News Headlines ({len(headlines)} articles)"]
        for h in headlines[:15]:
            lines.append(f"- {h}")
        parts.append("\n".join(lines))

    # Market news
    if market_news:
        lines = ["## General Market News"]
        for a in market_news[:5]:
            lines.append(f"- [{a.get('source', '')}] {a.get('headline', '')}")
        parts.append("\n".join(lines))

    # Portfolio context
    if portfolio_context:
        parts.append(f"## Portfolio Context\n{portfolio_context}")

    return "\n\n".join(parts)


VERDICT_ORDER = ["strong_sell", "sell", "neutral", "buy", "strong_buy"]


def _apply_verdict_adjustment(base_verdict: str, adjustment: str) -> str:
    """Shift verdict by ±1 step based on AI adjustment."""
    if adjustment not in ("upgrade", "downgrade"):
        return base_verdict
    idx = VERDICT_ORDER.index(base_verdict) if base_verdict in VERDICT_ORDER else 2
    if adjustment == "upgrade":
        idx = min(idx + 1, len(VERDICT_ORDER) - 1)
    else:
        idx = max(idx - 1, 0)
    return VERDICT_ORDER[idx]


def _parse_prediction_response(text: str, symbol: str, quant_scores: dict | None = None) -> dict | None:
    """Parse AI JSON response into prediction dict. Verdict/confidence come from quant engine."""
    try:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Mistral sometimes emits literal control characters inside JSON string
        # values (e.g. real newlines in ai_analysis). strict=False allows them.
        data = json.loads(cleaned, strict=False)
        if not isinstance(data, dict):
            return None

        # Verdict and confidence come from the quant engine
        if quant_scores and quant_scores.get("verdict"):
            verdict = quant_scores["verdict"]
            confidence = quant_scores["confidence"]
            # AI may adjust verdict ±1 step
            adjustment = data.get("verdict_adjustment", "none")
            verdict = _apply_verdict_adjustment(verdict, adjustment)
        else:
            # Fallback to AI verdict if no quant scores
            valid_verdicts = {"strong_buy", "buy", "neutral", "sell", "strong_sell"}
            verdict = data.get("verdict", "neutral")
            if verdict not in valid_verdicts:
                verdict = "neutral"
            confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))

        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "technical_summary": data.get("technical_summary", {}),
            "sentiment_summary": data.get("sentiment_summary", {}),
            "macro_summary": data.get("macro_summary", {}),
            "news_summary": data.get("news_summary", {}),
            "social_summary": data.get("social_summary", {}),
            "price_outlook": data.get("price_outlook", {}),
            "ai_analysis": str(data.get("ai_analysis", "")),
            "quant_scores": quant_scores or {},
        }
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning("Failed to parse prediction for %s: %s", symbol, e)
        return None


def _fallback_prediction(
    symbol: str,
    technical_data: dict | None,
    enhanced_sentiment: dict | None,
    macro_summary: dict,
    quant_scores: dict | None = None,
) -> dict:
    """Basic prediction when AI is unavailable. Uses quant verdict if available."""
    # Use quant engine verdict when available
    if quant_scores and quant_scores.get("verdict"):
        verdict = quant_scores["verdict"]
        confidence = quant_scores["confidence"]
    else:
        verdict = "neutral"
        confidence = 0.3

        if technical_data:
            tech_signal = technical_data.get("overall_signal", "neutral")
            if tech_signal == "bullish":
                verdict = "buy"
                confidence = 0.5
            elif tech_signal == "bearish":
                verdict = "sell"
                confidence = 0.5

    tech_signal = "neutral"
    if technical_data:
        tech_signal = technical_data.get("overall_signal", "neutral")

    sent_label = "neutral"
    if enhanced_sentiment:
        sent_label = enhanced_sentiment.get("unified_label", "neutral")

    return {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": confidence,
        "technical_summary": {"signal": tech_signal, "key_indicators": []},
        "sentiment_summary": {"unified_score": enhanced_sentiment.get("unified_score", 0) if enhanced_sentiment else 0, "label": sent_label},
        "macro_summary": {"environment": macro_summary.get("environment", "unknown"), "risk_level": macro_summary.get("risk_level", "unknown")},
        "news_summary": {"headline_count": 0, "overall_tone": "neutral"},
        "social_summary": {"buzz_level": "none", "total_mentions": 0},
        "price_outlook": {"short_term": "Análisis no disponible sin IA.", "medium_term": "Análisis no disponible sin IA."},
        "ai_analysis": "Predicción basada en motor cuantitativo. Configure MISTRAL_API_KEY para análisis narrativo completo.",
        "quant_scores": quant_scores or {},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
