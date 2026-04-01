"""Deterministic sentiment analysis with optional LLM narrative overlay."""

from __future__ import annotations

import json
import logging

from app.services.groq_service import groq_service
from app.services.sentiment_engine import classify_text_sentiment

logger = logging.getLogger(__name__)

EXPLANATION_PROMPT = """Explain the following structured sentiment snapshot for {symbol} ({asset_type}).

The score and label are already computed and MUST NOT be changed.
Use only the provided structured inputs. Do not invent extra data.

Structured inputs:
{payload}

Return ONLY valid JSON:
{{
  "narrative": "2-3 sentence explanation in plain language",
  "key_factors": ["factor 1", "factor 2", "factor 3"],
  "divergences": ["conflict 1", "conflict 2"],
  "strength": 1-5
}}
"""


def _clip(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _label(score: float) -> str:
    if score >= 0.2:
        return "bullish"
    if score <= -0.2:
        return "bearish"
    return "neutral"


def _technical_component(technical_data: dict | None) -> tuple[float, str | None]:
    if not technical_data:
        return 0.0, None
    overall = str(technical_data.get("overall_signal", "neutral")).lower()
    counts = technical_data.get("signal_counts", {})
    bullish = float(counts.get("bullish", 0) or 0)
    bearish = float(counts.get("bearish", 0) or 0)
    total = max(bullish + bearish + float(counts.get("neutral", 0) or 0), 1.0)
    balance = (bullish - bearish) / total
    overall_map = {"bullish": 0.4, "bearish": -0.4, "neutral": 0.0}
    value = _clip(balance * 0.6 + overall_map.get(overall, 0.0))
    factor = None
    if abs(value) >= 0.1:
        factor = f"Technical posture is {overall} with {int(bullish)}/{int(total)} bullish vs {int(bearish)} bearish signals."
    return value, factor


def _social_component(social_data: dict | None) -> tuple[float, str | None]:
    if not social_data:
        return 0.0, None
    score = float(social_data.get("combined_score", 0.0) or 0.0)
    mentions = int(social_data.get("total_mentions", 0) or 0)
    scaled = _clip(score * min(1.0, mentions / 20.0))
    factor = None
    if mentions > 0:
        factor = (
            f"Social flow is {social_data.get('sentiment_label', 'neutral')} with "
            f"{mentions} mentions and score {score:+.2f}."
        )
    return scaled, factor


def _news_component(news_headlines: list[str] | None) -> tuple[float, str | None]:
    if not news_headlines:
        return 0.0, None
    classified = [classify_text_sentiment(headline) for headline in news_headlines[:8] if headline]
    if not classified:
        return 0.0, None
    score = sum(float(item.get("score", 0.0) or 0.0) for item in classified) / len(classified)
    factor = f"News flow across {len(classified)} headlines is {_label(score)} ({score:+.2f})."
    return _clip(score), factor


def _price_component(quote_data: dict | None) -> tuple[float, str | None]:
    if not quote_data:
        return 0.0, None
    change_pct = float(quote_data.get("change_percent", 0.0) or 0.0)
    value = _clip(change_pct / 12.0, -0.35, 0.35)
    if abs(change_pct) < 1.0:
        return value, None
    direction = "up" if change_pct > 0 else "down"
    return value, f"Price is {direction} {change_pct:+.2f}% today."


def _build_deterministic_sentiment(
    symbol: str,
    quote_data: dict | None,
    technical_data: dict | None,
    social_data: dict | None,
    news_headlines: list[str] | None,
) -> dict:
    components = []
    factors: list[str] = []

    technical_score, technical_factor = _technical_component(technical_data)
    if technical_data:
        components.append(("technical", technical_score, 0.45))
    if technical_factor:
        factors.append(technical_factor)

    social_score, social_factor = _social_component(social_data)
    if social_data:
        components.append(("social", social_score, 0.25))
    if social_factor:
        factors.append(social_factor)

    news_score, news_factor = _news_component(news_headlines)
    if news_headlines:
        components.append(("news", news_score, 0.20))
    if news_factor:
        factors.append(news_factor)

    price_score, price_factor = _price_component(quote_data)
    if quote_data:
        components.append(("price", price_score, 0.10))
    if price_factor:
        factors.append(price_factor)

    total_weight = sum(weight for _, _, weight in components)
    score = (
        sum(value * weight for _, value, weight in components) / total_weight
        if total_weight > 0
        else 0.0
    )
    score = round(_clip(score), 2)
    label = _label(score)

    divergences: list[str] = []
    for left_index in range(len(components)):
        for right_index in range(left_index + 1, len(components)):
            left_name, left_score, _ = components[left_index]
            right_name, right_score, _ = components[right_index]
            if abs(left_score - right_score) >= 0.45:
                divergences.append(
                    f"{left_name.capitalize()} is {_label(left_score)} ({left_score:+.2f}) while {right_name} is {_label(right_score)} ({right_score:+.2f})."
                )

    agreement = 0
    signed_components = [value for _, value, _ in components if abs(value) >= 0.1]
    if signed_components:
        bullish_votes = sum(1 for value in signed_components if value > 0)
        bearish_votes = sum(1 for value in signed_components if value < 0)
        agreement = max(bullish_votes, bearish_votes)
    strength = max(1, min(5, agreement + (1 if abs(score) >= 0.45 else 0)))

    return {
        "symbol": symbol.upper(),
        "score": score,
        "label": label,
        "strength": strength,
        "sources_count": len(components),
        "narrative": _fallback_narrative(symbol, label, score, factors, divergences),
        "key_factors": factors[:4],
        "divergences": divergences[:4],
    }


def _fallback_narrative(
    symbol: str,
    label: str,
    score: float,
    factors: list[str],
    divergences: list[str],
) -> str:
    if not factors:
        return (
            f"Sentiment for {symbol.upper()} is neutral because there is not enough structured coverage "
            "to support a directional view."
        )
    summary = f"Structured sentiment for {symbol.upper()} is {label} ({score:+.2f})."
    if divergences:
        return f"{summary} Signals are mixed, with the main conflict being: {divergences[0]}"
    return f"{summary} Main drivers: {'; '.join(factors[:2])}"


def _parse_sentiment_response(text: str, symbol: str) -> dict:
    """Parse the optional narrative overlay into a sentiment dict."""
    try:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            json_lines = []
            in_json = False
            for line in lines:
                if line.strip().startswith("```") and not in_json:
                    in_json = True
                    continue
                if line.strip() == "```":
                    break
                if in_json:
                    json_lines.append(line)
            cleaned = "\n".join(json_lines)

        data = json.loads(cleaned)
        divergences = data.get("divergences", [])
        if not isinstance(divergences, list):
            divergences = []

        return {
            "symbol": symbol.upper(),
            "score": round(_clip(float(data.get("score", 0.0) or 0.0)), 2),
            "label": _label(float(data.get("score", 0.0) or 0.0)),
            "strength": max(1, min(5, int(data.get("strength", 3) or 3))),
            "sources_count": int(data.get("sources_count", 0) or 0),
            "narrative": str(data.get("narrative", "")),
            "key_factors": [str(item) for item in data.get("key_factors", [])[:5]],
            "divergences": [str(item) for item in divergences[:5]],
        }
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Failed to parse sentiment narrative overlay for %s: %s", symbol, exc)
        return _default_sentiment(symbol)


def _default_sentiment(symbol: str) -> dict:
    return {
        "symbol": symbol.upper(),
        "score": 0.0,
        "label": "neutral",
        "strength": 1,
        "sources_count": 0,
        "narrative": "Structured sentiment is unavailable.",
        "key_factors": [],
        "divergences": [],
    }


async def _explain_sentiment(
    symbol: str,
    asset_type: str,
    payload: dict,
) -> dict | None:
    if not groq_service.is_available():
        return None
    try:
        response_text = await groq_service.chat(
            prompt=EXPLANATION_PROMPT.format(
                symbol=symbol.upper(),
                asset_type=asset_type,
                payload=json.dumps(payload, ensure_ascii=True),
            ),
            model="fast",
            temperature=0.2,
        )
        return _parse_sentiment_response(response_text, symbol)
    except Exception as exc:
        logger.warning("Sentiment explanation failed for %s: %s", symbol, exc)
        return None


async def analyze_sentiment(
    symbol: str,
    asset_type: str = "stock",
    quote_data: dict | None = None,
    technical_data: dict | None = None,
    social_data: dict | None = None,
    news_headlines: list[str] | None = None,
) -> dict:
    deterministic = _build_deterministic_sentiment(
        symbol,
        quote_data,
        technical_data,
        social_data,
        news_headlines,
    )
    explained = await _explain_sentiment(symbol, asset_type, deterministic)
    if not explained:
        return deterministic

    deterministic["narrative"] = explained.get("narrative") or deterministic["narrative"]
    deterministic["key_factors"] = explained.get("key_factors") or deterministic["key_factors"]
    deterministic["divergences"] = explained.get("divergences") or deterministic["divergences"]
    deterministic["strength"] = max(
        deterministic.get("strength", 1),
        int(explained.get("strength", deterministic.get("strength", 1)) or deterministic.get("strength", 1)),
    )
    return deterministic
