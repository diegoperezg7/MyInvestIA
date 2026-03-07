from unittest.mock import AsyncMock, patch

import pytest

from app.services.ai_explanation_layer import (
    _clip,
    _signal_from_rating,
    _collect_warnings,
    _contradictions,
    _confidence,
    _fallback_summary,
    explain_asset_analysis,
)


def _score_payload() -> dict:
    return {
        "symbol": "AAPL",
        "asset_type": "stock",
        "quote": {
            "price": 200.0,
            "change_percent": 1.2,
            "name": "Apple",
            "currency": "USD",
        },
        "fundamentals_score": {
            "value": 72.0,
            "sources": ["Yahoo Finance"],
            "warnings": [],
        },
        "technical_score": {
            "value": 66.0,
            "sources": ["technical_analysis"],
            "warnings": [],
        },
        "sentiment_score": {
            "value": 38.0,
            "sources": ["Structured News Flow"],
            "warnings": [
                "Coverage is thin; sentiment should be treated as low confidence."
            ],
            "inputs_used": {
                "divergences": [
                    "News flow is bearish while technicals remain positive."
                ]
            },
        },
        "macro_score": {"value": 42.0, "sources": ["FRED"], "warnings": []},
        "portfolio_fit_score": {
            "value": 35.0,
            "sources": ["portfolio_intelligence"],
            "warnings": [],
        },
        "total_score": {
            "value": 58.0,
            "sources": [
                "Yahoo Finance",
                "technical_analysis",
                "Structured News Flow",
                "FRED",
                "portfolio_intelligence",
            ],
            "warnings": [
                "Coverage is thin; sentiment should be treated as low confidence."
            ],
            "inputs_used": {"rating": "neutral"},
        },
        "quant_overlay": {"confidence": 0.62},
    }


@pytest.mark.asyncio
async def test_explain_asset_analysis_falls_back_without_llm():
    with (
        patch(
            "app.services.ai_explanation_layer.build_asset_score",
            new_callable=AsyncMock,
            return_value=_score_payload(),
        ),
        patch(
            "app.services.ai_explanation_layer._llm_summary",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        result = await explain_asset_analysis(
            "AAPL", user_id="user-1", tenant_id="default"
        )

    assert result["symbol"] == "AAPL"
    assert result["signal"] == "neutral"
    assert result["warnings"]
    assert result["contradictory_signals"]
    assert result["decision_support_only"] is True


@pytest.mark.asyncio
async def test_explain_asset_analysis_uses_llm_summary_when_available():
    with (
        patch(
            "app.services.ai_explanation_layer.build_asset_score",
            new_callable=AsyncMock,
            return_value=_score_payload(),
        ),
        patch(
            "app.services.ai_explanation_layer.groq_service.is_available",
            return_value=True,
        ),
        patch(
            "app.services.ai_explanation_layer.groq_service.chat",
            new_callable=AsyncMock,
            return_value="Short structured explanation.",
        ),
    ):
        result = await explain_asset_analysis("AAPL")

    assert result["summary"] == "Short structured explanation."
    assert result["sources"]


def test_clip():
    assert _clip(0.5) == 0.5
    assert _clip(1.5) == 1.0
    assert _clip(-0.5) == 0.0
    assert _clip(0.5, lo=0.2, hi=0.8) == 0.5
    assert _clip(0.1, lo=0.2, hi=0.8) == 0.2
    assert _clip(0.9, lo=0.2, hi=0.8) == 0.8


def test_signal_from_rating():
    assert _signal_from_rating("strong_positive") == "bullish"
    assert _signal_from_rating("positive") == "bullish"
    assert _signal_from_rating("negative") == "bearish"
    assert _signal_from_rating("cautious") == "bearish"
    assert _signal_from_rating("neutral") == "neutral"


def test_collect_warnings():
    payload = {
        "fundamentals_score": {"warnings": ["Low coverage"]},
        "technical_score": {"warnings": []},
        "sentiment_score": {"warnings": ["Single source"]},
        "macro_score": {"warnings": []},
        "portfolio_fit_score": {"warnings": []},
        "total_score": {"warnings": ["Divergence"]},
    }
    warnings = _collect_warnings(payload)
    assert "Low coverage" in warnings
    assert "Single source" in warnings
    assert "Divergence" in warnings


def test_collect_warnings_deduplicates():
    payload = {
        "fundamentals_score": {"warnings": ["Low coverage"]},
        "technical_score": {"warnings": ["Low coverage"]},
        "sentiment_score": {"warnings": []},
        "macro_score": {"warnings": []},
        "portfolio_fit_score": {"warnings": []},
        "total_score": {"warnings": []},
    }
    warnings = _collect_warnings(payload)
    assert warnings.count("Low coverage") == 1


def test_collect_warnings_respects_limit():
    payload = {f"score_{i}": {"warnings": [f"warning_{i}"]} for i in range(10)}
    payload.update(
        {
            "fundamentals_score": {"warnings": []},
            "technical_score": {"warnings": []},
            "sentiment_score": {"warnings": []},
            "macro_score": {"warnings": []},
            "portfolio_fit_score": {"warnings": []},
            "total_score": {"warnings": []},
        }
    )
    warnings = _collect_warnings(payload)
    assert len(warnings) <= 8


def test_contradictions_detects_technical_sentiment_divergence():
    payload = {
        "fundamentals_score": {"value": 50.0},
        "technical_score": {"value": 70.0},
        "sentiment_score": {"value": 30.0, "inputs_used": {}},
        "macro_score": {"value": 50.0},
        "portfolio_fit_score": {"value": 50.0},
        "total_score": {"value": 50.0},
    }
    result = _contradictions(payload)
    assert any("technical" in c.lower() and "sentiment" in c.lower() for c in result)


def test_contradictions_detects_sentiment_technical_divergence():
    payload = {
        "fundamentals_score": {"value": 50.0},
        "technical_score": {"value": 30.0},
        "sentiment_score": {"value": 70.0, "inputs_used": {}},
        "macro_score": {"value": 50.0},
        "portfolio_fit_score": {"value": 50.0},
        "total_score": {"value": 50.0},
    }
    result = _contradictions(payload)
    assert any("sentiment" in c.lower() and "technical" in c.lower() for c in result)


def test_contradictions_detects_fundamentals_macro_divergence():
    payload = {
        "fundamentals_score": {"value": 70.0},
        "technical_score": {"value": 50.0},
        "sentiment_score": {"value": 50.0, "inputs_used": {}},
        "macro_score": {"value": 30.0},
        "portfolio_fit_score": {"value": 50.0},
        "total_score": {"value": 50.0},
    }
    result = _contradictions(payload)
    assert any("fundamentals" in c.lower() or "macro" in c.lower() for c in result)


def test_contradictions_detects_portfolio_fit_divergence():
    payload = {
        "fundamentals_score": {"value": 50.0},
        "technical_score": {"value": 50.0},
        "sentiment_score": {"value": 50.0, "inputs_used": {}},
        "macro_score": {"value": 50.0},
        "portfolio_fit_score": {"value": 30.0},
        "total_score": {"value": 70.0},
    }
    result = _contradictions(payload)
    assert any("portfolio" in c.lower() for c in result)


def test_contradictions_includes_sentiment_divergences():
    payload = {
        "fundamentals_score": {"value": 50.0},
        "technical_score": {"value": 50.0},
        "sentiment_score": {
            "value": 50.0,
            "inputs_used": {"divergences": ["news diverges from social"]},
        },
        "macro_score": {"value": 50.0},
        "portfolio_fit_score": {"value": 50.0},
        "total_score": {"value": 50.0},
    }
    result = _contradictions(payload)
    assert "news diverges from social" in result


def test_contradictions_respects_limit():
    payload = {
        "fundamentals_score": {"value": 80.0},
        "technical_score": {"value": 20.0},
        "sentiment_score": {"value": 20.0, "inputs_used": {}},
        "macro_score": {"value": 80.0},
        "portfolio_fit_score": {"value": 20.0},
        "total_score": {"value": 70.0},
    }
    result = _contradictions(payload)
    assert len(result) <= 6


def test_confidence_high_with_good_quant_and_components():
    payload = {
        "quant_overlay": {"confidence": 0.8},
        "fundamentals_score": {"value": 70.0},
        "technical_score": {"value": 65.0},
        "sentiment_score": {"value": 60.0},
        "macro_score": {"value": 55.0},
        "portfolio_fit_score": {"value": 60.0},
    }
    contradictions = []
    warnings = []
    conf, label = _confidence(payload, contradictions, warnings)
    assert conf >= 0.5
    assert label == "high"


def test_confidence_low_with_many_contradictions():
    payload = {
        "quant_overlay": {"confidence": 0.5},
        "fundamentals_score": {"value": 70.0},
        "technical_score": {"value": 30.0},
        "sentiment_score": {"value": 70.0},
        "macro_score": {"value": 30.0},
        "portfolio_fit_score": {"value": 70.0},
    }
    contradictions = [
        "contradiction 1",
        "contradiction 2",
        "contradiction 3",
        "contradiction 4",
    ]
    warnings = ["warning 1", "warning 2", "warning 3", "warning 4"]
    conf, label = _confidence(payload, contradictions, warnings)
    assert conf < 0.5
    assert label == "low"


def test_confidence_label_medium():
    payload = {
        "quant_overlay": {"confidence": 0.7},
        "fundamentals_score": {"value": 60.0},
        "technical_score": {"value": 50.0},
        "sentiment_score": {"value": 40.0},
        "macro_score": {"value": 50.0},
        "portfolio_fit_score": {"value": 55.0},
    }
    contradictions = []
    warnings = []
    conf, label = _confidence(payload, contradictions, warnings)
    assert label == "medium"


def test_fallback_summary_includes_components():
    payload = {
        "fundamentals_score": {"value": 70.0},
        "technical_score": {"value": 60.0},
        "sentiment_score": {"value": 40.0},
        "macro_score": {"value": 50.0},
        "portfolio_fit_score": {"value": 55.0},
        "total_score": {"value": 55.0, "inputs_used": {"rating": "positive"}},
    }
    result = _fallback_summary("AAPL", payload, [], [])
    assert "AAPL" in result
    assert "positive" in result.lower()
    assert "fundamentals" in result.lower()


def test_fallback_summary_includes_contradiction():
    payload = {
        "fundamentals_score": {"value": 50.0},
        "technical_score": {"value": 50.0},
        "sentiment_score": {"value": 50.0},
        "macro_score": {"value": 50.0},
        "portfolio_fit_score": {"value": 50.0},
        "total_score": {"value": 50.0, "inputs_used": {"rating": "neutral"}},
    }
    result = _fallback_summary(
        "AAPL", payload, ["technical weak, sentiment strong"], []
    )
    assert "contradiction" in result.lower()


def test_fallback_summary_includes_warning():
    payload = {
        "fundamentals_score": {"value": 50.0},
        "technical_score": {"value": 50.0},
        "sentiment_score": {"value": 50.0},
        "macro_score": {"value": 50.0},
        "portfolio_fit_score": {"value": 50.0},
        "total_score": {"value": 50.0, "inputs_used": {"rating": "neutral"}},
    }
    result = _fallback_summary("AAPL", payload, [], ["Low coverage"])
    assert "caution" in result.lower()


def test_fallback_summary_identifies_strongest_weakest():
    payload = {
        "fundamentals_score": {"value": 80.0},
        "technical_score": {"value": 30.0},
        "sentiment_score": {"value": 50.0},
        "macro_score": {"value": 50.0},
        "portfolio_fit_score": {"value": 50.0},
        "total_score": {"value": 50.0, "inputs_used": {"rating": "neutral"}},
    }
    result = _fallback_summary("AAPL", payload, [], [])
    assert "fundamentals" in result.lower()
    assert "technical" in result.lower()
