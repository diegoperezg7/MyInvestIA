"""Multi-step analysis pipeline with SSE progress streaming.

Orchestrates 7 analysis steps, yielding progress events after each step.
"""

import json
import logging
import time
from typing import AsyncGenerator

from app.schemas.pipeline import PIPELINE_STEPS, PipelineStep, PipelineStepStatus, PipelineStatus
from app.services.ai_service import ai_service
from app.services.market_data import market_data_service
from app.services.signal_aggregator import build_signal_summary
from app.services.technical_analysis import compute_all_indicators

logger = logging.getLogger(__name__)


async def run_analysis_pipeline(symbol: str) -> AsyncGenerator[str, None]:
    """Run the 7-step analysis pipeline, yielding SSE events.

    Each event is a JSON string with the current PipelineStatus.
    """
    symbol = symbol.upper()
    steps = [
        PipelineStep(id=s["id"], name=s["name"], description=s["description"])
        for s in PIPELINE_STEPS
    ]
    status = PipelineStatus(symbol=symbol, steps=steps, total_steps=len(steps))

    # Accumulated data
    quote_data = None
    history = None
    indicators = None
    signal_summary = None
    sentiment_text = ""

    for i, step in enumerate(steps):
        status.current_step = i + 1
        step.status = PipelineStepStatus.RUNNING
        yield _sse_event(status)

        start = time.monotonic()
        try:
            if step.id == "quote":
                quote_data = await market_data_service.get_quote(symbol)
                step.result = {"price": quote_data["price"], "change": quote_data["change_percent"]} if quote_data else {}

            elif step.id == "history":
                history = await market_data_service.get_history(symbol, period="6mo", interval="1d")
                step.result = {"data_points": len(history)} if history else {}

            elif step.id == "technicals":
                if history and len(history) >= 30:
                    closes = [r["close"] for r in history]
                    indicators = compute_all_indicators(closes)
                    step.result = {
                        "overall_signal": indicators.get("overall_signal", "neutral"),
                        "signal_counts": indicators.get("signal_counts", {}),
                    }
                else:
                    step.status = PipelineStepStatus.SKIPPED
                    step.result = {"reason": "Insufficient history"}

            elif step.id == "signals":
                if indicators:
                    closes = [r["close"] for r in history]
                    price = closes[-1] if closes else None
                    signal_summary = build_signal_summary(symbol, indicators, price)
                    step.result = {
                        "overall": signal_summary.overall.value,
                        "confidence": signal_summary.overall_confidence,
                    }
                else:
                    step.status = PipelineStepStatus.SKIPPED

            elif step.id == "sentiment":
                if ai_service.is_configured and quote_data:
                    try:
                        from app.services.sentiment_service import analyze_sentiment
                        sent = await analyze_sentiment(
                            symbol=symbol,
                            asset_type="stock",
                            quote_data=quote_data,
                            technical_data=indicators,
                        )
                        sentiment_text = sent.get("narrative", "")
                        step.result = {"label": sent.get("label", "neutral"), "score": sent.get("score", 0)}
                    except Exception:
                        step.status = PipelineStepStatus.SKIPPED
                        step.result = {"reason": "Sentiment analysis unavailable"}
                else:
                    step.status = PipelineStepStatus.SKIPPED

            elif step.id == "macro":
                try:
                    from app.services.macro_intelligence import get_all_macro_indicators, get_macro_summary
                    raw = get_all_macro_indicators()
                    summary = get_macro_summary(raw)
                    step.result = {
                        "environment": summary.get("environment", "unknown"),
                        "risk_level": summary.get("risk_level", "unknown"),
                    }
                except Exception:
                    step.status = PipelineStepStatus.SKIPPED

            elif step.id == "synthesis":
                if ai_service.is_configured:
                    try:
                        result = await ai_service.analyze_asset(
                            symbol=symbol,
                            technical_data=indicators,
                            quote_data=quote_data,
                        )
                        status.final_analysis = result.get("summary", "")
                        status.signal = result.get("signal", "neutral")
                        status.confidence = result.get("confidence", 0.5)
                        step.result = {"signal": result.get("signal"), "confidence": result.get("confidence")}
                    except Exception as e:
                        step.error = str(e)
                        step.status = PipelineStepStatus.FAILED
                else:
                    # Use rule engine as fallback
                    if signal_summary:
                        status.signal = signal_summary.overall.value
                        status.confidence = signal_summary.overall_confidence / 100
                        status.final_analysis = f"Rule-based analysis for {symbol}: {signal_summary.overall.value} signal with {signal_summary.overall_confidence:.0f}% confidence based on {len(signal_summary.signals)} indicators."
                    step.result = {"source": "rule_engine"}

            if step.status == PipelineStepStatus.RUNNING:
                step.status = PipelineStepStatus.COMPLETED

        except Exception as e:
            logger.warning("Pipeline step %s failed for %s: %s", step.id, symbol, e)
            step.status = PipelineStepStatus.FAILED
            step.error = str(e)

        step.duration_ms = int((time.monotonic() - start) * 1000)
        yield _sse_event(status)

    status.completed = True
    yield _sse_event(status)


def _sse_event(status: PipelineStatus) -> str:
    """Format as SSE event."""
    data = status.model_dump(mode="json")
    return f"data: {json.dumps(data)}\n\n"
