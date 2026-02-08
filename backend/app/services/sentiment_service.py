"""Sentiment analysis service using Claude API.

Analyzes market sentiment for assets by asking Claude to assess the current
market narrative based on its training data knowledge. Returns a structured
sentiment assessment with score, label, and narrative.
"""

import json
import logging

from app.config import settings
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)

SENTIMENT_PROMPT = """Analyze the current market sentiment for {symbol} ({asset_type}).

{context}

Provide your assessment in the following JSON format ONLY (no other text):
{{
  "score": <float from -1.0 (very bearish) to 1.0 (very bullish)>,
  "label": "<bullish|bearish|neutral>",
  "sources_count": <number of distinct data points or factors you considered>,
  "narrative": "<2-3 sentence summary of the current sentiment landscape>",
  "key_factors": [
    "<factor 1>",
    "<factor 2>",
    "<factor 3>"
  ]
}}

Base your analysis on:
- Recent price action and volume patterns
- Technical indicator signals (if provided)
- Known fundamental factors for this asset
- General market conditions
- Sector/industry trends

Be honest about uncertainty. If you lack recent data, reflect that in a lower confidence score closer to 0."""


async def analyze_sentiment(
    symbol: str,
    asset_type: str = "stock",
    quote_data: dict | None = None,
    technical_data: dict | None = None,
) -> dict:
    """Analyze market sentiment for an asset using Claude.

    Args:
        symbol: Asset ticker symbol
        asset_type: Type of asset (stock, etf, crypto, commodity)
        quote_data: Optional current price/volume data
        technical_data: Optional technical indicators

    Returns:
        Dict with: score, label, sources_count, narrative, key_factors
    """
    if not ai_service.is_configured:
        return _default_sentiment(symbol)

    # Build context from available data
    context_parts = []
    if quote_data:
        context_parts.append(
            f"Current Price: ${quote_data.get('price', 'N/A')}, "
            f"Change: {quote_data.get('change_percent', 'N/A')}%, "
            f"Volume: {quote_data.get('volume', 'N/A')}"
        )

    if technical_data:
        overall = technical_data.get("overall_signal", "N/A")
        rsi_val = technical_data.get("rsi", {}).get("value", "N/A")
        rsi_sig = technical_data.get("rsi", {}).get("signal", "N/A")
        macd_sig = technical_data.get("macd", {}).get("signal", "N/A")
        context_parts.append(
            f"Technical signals: Overall={overall}, RSI={rsi_val} ({rsi_sig}), MACD={macd_sig}"
        )

    context = "\n".join(context_parts) if context_parts else "No additional market data available."

    prompt = SENTIMENT_PROMPT.format(
        symbol=symbol.upper(),
        asset_type=asset_type,
        context=context,
    )

    try:
        response_text = await ai_service.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )

        return _parse_sentiment_response(response_text, symbol)
    except Exception as e:
        logger.warning("Sentiment analysis failed for %s: %s", symbol, e)
        return _default_sentiment(symbol)


def _parse_sentiment_response(text: str, symbol: str) -> dict:
    """Parse Claude's JSON response into a sentiment dict."""
    try:
        # Try to extract JSON from the response
        # Claude might wrap it in markdown code blocks
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last lines (```json and ```)
            json_lines = []
            in_json = False
            for line in lines:
                if line.strip().startswith("```") and not in_json:
                    in_json = True
                    continue
                elif line.strip() == "```":
                    break
                elif in_json:
                    json_lines.append(line)
            cleaned = "\n".join(json_lines)

        data = json.loads(cleaned)

        # Validate and clamp score
        score = float(data.get("score", 0.0))
        score = max(-1.0, min(1.0, score))

        # Validate label
        label = data.get("label", "neutral").lower()
        if label not in ("bullish", "bearish", "neutral"):
            label = "bullish" if score > 0.2 else "bearish" if score < -0.2 else "neutral"

        return {
            "symbol": symbol.upper(),
            "score": round(score, 2),
            "label": label,
            "sources_count": int(data.get("sources_count", 0)),
            "narrative": str(data.get("narrative", "")),
            "key_factors": data.get("key_factors", []),
        }
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("Failed to parse sentiment response for %s: %s", symbol, e)
        return _default_sentiment(symbol)


def _default_sentiment(symbol: str) -> dict:
    """Return a neutral default sentiment when analysis is unavailable."""
    return {
        "symbol": symbol.upper(),
        "score": 0.0,
        "label": "neutral",
        "sources_count": 0,
        "narrative": "Sentiment analysis unavailable. Configure ANTHROPIC_API_KEY for AI-powered analysis.",
        "key_factors": [],
    }
