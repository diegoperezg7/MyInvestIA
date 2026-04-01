"""AI explanation layer that translates structured analytics into user-facing summaries."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.services.ai_service import MODEL_ANALYSIS, ai_service
from app.services.groq_service import groq_service
from app.services.scoring_engine import build_asset_score

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the MyInvestIA explanation layer.

Your job is to explain already-computed analytics. You are NOT the decision engine.

Rules:
- Use only the structured payload provided.
- Do not invent prices, catalysts, fundamentals, or portfolio facts.
- Explicitly reflect uncertainty and contradictory signals.
- Do not present the output as financial advice.
- Prefer concise, concrete language.
"""


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clip(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _signal_from_rating(rating: str) -> str:
    if rating in {"strong_positive", "positive"}:
        return "bullish"
    if rating in {"negative", "cautious"}:
        return "bearish"
    return "neutral"


def _collect_warnings(score_payload: dict) -> list[str]:
    warnings: list[str] = []
    for key in (
        "fundamentals_score",
        "technical_score",
        "sentiment_score",
        "macro_score",
        "portfolio_fit_score",
        "total_score",
    ):
        component = score_payload.get(key, {})
        for warning in component.get("warnings", []):
            if warning not in warnings:
                warnings.append(warning)
    return warnings[:8]


def _contradictions(score_payload: dict) -> list[str]:
    component_values = {
        "fundamentals": float(score_payload.get("fundamentals_score", {}).get("value", 50.0) or 50.0),
        "technical": float(score_payload.get("technical_score", {}).get("value", 50.0) or 50.0),
        "sentiment": float(score_payload.get("sentiment_score", {}).get("value", 50.0) or 50.0),
        "macro": float(score_payload.get("macro_score", {}).get("value", 50.0) or 50.0),
        "portfolio_fit": float(score_payload.get("portfolio_fit_score", {}).get("value", 50.0) or 50.0),
        "total_score": float(score_payload.get("total_score", {}).get("value", 50.0) or 50.0),
    }
    contradictions: list[str] = []
    if component_values["technical"] >= 60 and component_values["sentiment"] <= 40:
        contradictions.append("Technicals are positive while sentiment remains weak.")
    if component_values["technical"] <= 40 and component_values["sentiment"] >= 60:
        contradictions.append("Sentiment is positive while technicals remain weak.")
    if component_values["fundamentals"] >= 65 and component_values["macro"] <= 40:
        contradictions.append("Company-level quality is stronger than the current macro backdrop.")
    if component_values["portfolio_fit"] <= 40 and component_values["total_score"] >= 60:
        contradictions.append("Standalone attractiveness is better than portfolio fit.")
    sentiment_inputs = score_payload.get("sentiment_score", {}).get("inputs_used", {})
    for divergence in sentiment_inputs.get("divergences", [])[:2]:
        if divergence not in contradictions:
            contradictions.append(str(divergence))
    return contradictions[:6]


def _confidence(score_payload: dict, contradictions: list[str], warnings: list[str]) -> tuple[float, str]:
    quant_confidence = float(score_payload.get("quant_overlay", {}).get("confidence", 0.5) or 0.5)
    non_neutral_components = sum(
        1
        for key in ("fundamentals_score", "technical_score", "sentiment_score", "macro_score", "portfolio_fit_score")
        if abs(float(score_payload.get(key, {}).get("value", 50.0) or 50.0) - 50.0) >= 8.0
    )
    raw = 0.35 + quant_confidence * 0.35 + min(non_neutral_components / 5.0, 1.0) * 0.15
    raw -= min(len(contradictions) * 0.05, 0.15)
    raw -= min(len(warnings) * 0.03, 0.12)
    confidence = round(_clip(raw), 4)
    if confidence >= 0.72:
        label = "high"
    elif confidence >= 0.48:
        label = "medium"
    else:
        label = "low"
    return confidence, label


def _fallback_summary(
    symbol: str,
    score_payload: dict,
    contradictions: list[str],
    warnings: list[str],
) -> str:
    total_inputs = score_payload.get("total_score", {}).get("inputs_used", {})
    rating = total_inputs.get("rating", "neutral")
    total_score = float(score_payload.get("total_score", {}).get("value", 50.0) or 50.0)
    components = {
        "fundamentals": float(score_payload.get("fundamentals_score", {}).get("value", 50.0) or 50.0),
        "technical": float(score_payload.get("technical_score", {}).get("value", 50.0) or 50.0),
        "sentiment": float(score_payload.get("sentiment_score", {}).get("value", 50.0) or 50.0),
        "macro": float(score_payload.get("macro_score", {}).get("value", 50.0) or 50.0),
        "portfolio fit": float(score_payload.get("portfolio_fit_score", {}).get("value", 50.0) or 50.0),
    }
    strongest = max(components.items(), key=lambda item: item[1])
    weakest = min(components.items(), key=lambda item: item[1])
    summary = (
        f"{symbol} currently maps to a {rating} setup with total score {total_score:.1f}/100. "
        f"The strongest component is {strongest[0]} ({strongest[1]:.1f}) while the weakest is {weakest[0]} ({weakest[1]:.1f})."
    )
    if contradictions:
        summary += f" Main contradiction: {contradictions[0]}"
    elif warnings:
        summary += f" Key caution: {warnings[0]}"
    return summary


async def _llm_summary(prompt_payload: dict) -> str | None:
    prompt = (
        "Explain this asset analysis in 2 short paragraphs. Include the strongest bull point, the strongest bear point, "
        "and mention uncertainty explicitly.\n\n"
        f"{json.dumps(prompt_payload, ensure_ascii=True)}"
    )
    try:
        if groq_service.is_available():
            return await groq_service.chat(
                prompt=prompt,
                model="powerful",
                system_prompt=SYSTEM_PROMPT,
                temperature=0.2,
            )
        if ai_service.is_configured:
            return await ai_service.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                model=MODEL_ANALYSIS,
                system_override=SYSTEM_PROMPT,
            )
    except Exception as exc:
        logger.warning("AI explanation generation failed: %s", exc)
    return None


async def explain_asset_analysis(
    symbol: str,
    *,
    asset_type: str | None = None,
    user_id: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    payload = await build_asset_score(
        symbol,
        asset_type=asset_type,
        user_id=user_id,
        tenant_id=tenant_id,
    )
    warnings = _collect_warnings(payload)
    contradictions = _contradictions(payload)
    confidence, confidence_label = _confidence(payload, contradictions, warnings)
    total_inputs = payload.get("total_score", {}).get("inputs_used", {})
    rating = str(total_inputs.get("rating", "neutral"))
    signal = _signal_from_rating(rating)
    sources = sorted(
        {
            source
            for key in (
                "fundamentals_score",
                "technical_score",
                "sentiment_score",
                "macro_score",
                "portfolio_fit_score",
                "total_score",
            )
            for source in payload.get(key, {}).get("sources", [])
        }
    )

    prompt_payload = {
        "symbol": payload.get("symbol"),
        "asset_type": payload.get("asset_type"),
        "quote": payload.get("quote"),
        "total_score": payload.get("total_score", {}),
        "component_scores": {
            "fundamentals_score": payload.get("fundamentals_score", {}).get("value", 50.0),
            "technical_score": payload.get("technical_score", {}).get("value", 50.0),
            "sentiment_score": payload.get("sentiment_score", {}).get("value", 50.0),
            "macro_score": payload.get("macro_score", {}).get("value", 50.0),
            "portfolio_fit_score": payload.get("portfolio_fit_score", {}).get("value", 50.0),
        },
        "warnings": warnings,
        "contradictions": contradictions,
        "sources": sources,
    }
    summary = await _llm_summary(prompt_payload)
    if not summary:
        summary = _fallback_summary(symbol.upper(), payload, contradictions, warnings)

    return {
        "symbol": payload.get("symbol", symbol.upper()),
        "summary": summary.strip(),
        "signal": signal,
        "confidence": confidence,
        "confidence_label": confidence_label,
        "warnings": warnings,
        "contradictory_signals": contradictions,
        "sources": sources,
        "component_scores": {
            "fundamentals_score": float(payload.get("fundamentals_score", {}).get("value", 50.0) or 50.0),
            "technical_score": float(payload.get("technical_score", {}).get("value", 50.0) or 50.0),
            "sentiment_score": float(payload.get("sentiment_score", {}).get("value", 50.0) or 50.0),
            "macro_score": float(payload.get("macro_score", {}).get("value", 50.0) or 50.0),
            "portfolio_fit_score": float(payload.get("portfolio_fit_score", {}).get("value", 50.0) or 50.0),
            "total_score": float(payload.get("total_score", {}).get("value", 50.0) or 50.0),
        },
        "generated_at": _iso_now(),
        "decision_support_only": True,
    }
