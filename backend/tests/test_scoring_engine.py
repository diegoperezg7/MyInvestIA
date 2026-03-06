from unittest.mock import AsyncMock, patch

import pytest

from app.services.scoring_engine import build_asset_score


def _history(days: int = 90, start: float = 100.0, step: float = 0.8) -> list[dict]:
    rows = []
    for index in range(days):
        close = start + index * step
        rows.append(
            {
                "date": f"2026-01-{(index % 28) + 1:02d}T00:00:00+00:00",
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1_000_000 + index * 1_000,
            }
        )
    return rows


def _macro() -> list[dict]:
    return [
        {"name": "VIX (Volatility Index)", "value": 16.0, "change_percent": -1.2, "source": "FRED"},
        {"name": "US Dollar Index (DXY)", "value": 103.0, "change_percent": -0.3, "source": "FRED"},
        {"name": "10-Year Treasury Yield", "value": 4.1, "change_percent": -0.1, "source": "FRED"},
        {"name": "13-Week T-Bill Rate", "value": 3.9, "change_percent": 0.0, "source": "FRED"},
    ]


def _fundamentals() -> dict:
    return {
        "source": "Yahoo Finance",
        "company_info": {"sector": "Technology", "country": "United States"},
        "ratios": {
            "roe": 0.24,
            "profit_margins": 0.28,
            "debt_to_equity": 40.0,
            "current_ratio": 1.8,
            "pe_forward": 24.0,
            "price_to_book": 6.5,
        },
        "growth": {
            "revenue_growth": 0.12,
            "earnings_growth": 0.18,
        },
    }


def _sentiment() -> dict:
    return {
        "unified_score": 0.42,
        "unified_label": "bullish",
        "coverage_confidence": 0.75,
        "sources": [
            {"source_name": "news", "score": 0.4, "weight": 0.4},
            {"source_name": "social", "score": 0.5, "weight": 0.3},
            {"source_name": "ai", "score": 0.35, "weight": 0.3},
        ],
    }


@pytest.mark.asyncio
async def test_build_asset_score_returns_structured_components():
    with patch(
        "app.services.scoring_engine.market_data_service.get_quote",
        new_callable=AsyncMock,
        return_value={
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "price": 210.0,
            "change_percent": 1.4,
            "currency": "USD",
        },
    ), patch(
        "app.services.scoring_engine.market_data_service.get_history",
        new_callable=AsyncMock,
        return_value=_history(),
    ), patch(
        "app.services.scoring_engine.get_fundamentals",
        new_callable=AsyncMock,
        return_value=_fundamentals(),
    ), patch(
        "app.services.scoring_engine.get_enhanced_sentiment",
        new_callable=AsyncMock,
        return_value=_sentiment(),
    ), patch(
        "app.services.scoring_engine.get_all_macro_indicators",
        new_callable=AsyncMock,
        return_value=_macro(),
    ):
        result = await build_asset_score("AAPL")

    assert result["symbol"] == "AAPL"
    assert result["fundamentals_score"]["value"] > 50
    assert result["technical_score"]["value"] > 50
    assert result["sentiment_score"]["value"] > 50
    assert result["macro_score"]["value"] > 50
    assert result["portfolio_fit_score"]["value"] == 50.0
    assert result["total_score"]["value"] > 55
    assert result["decision_support_only"] is True


@pytest.mark.asyncio
async def test_build_asset_score_handles_missing_data_gracefully():
    with patch(
        "app.services.scoring_engine.market_data_service.get_quote",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "app.services.scoring_engine.market_data_service.get_history",
        new_callable=AsyncMock,
        return_value=[],
    ), patch(
        "app.services.scoring_engine.get_fundamentals",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "app.services.scoring_engine.get_enhanced_sentiment",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "app.services.scoring_engine.get_all_macro_indicators",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = await build_asset_score("UNKNOWN")

    assert result["total_score"]["value"] == 50.0
    assert result["fundamentals_score"]["warnings"]
    assert result["technical_score"]["warnings"]
    assert result["sentiment_score"]["warnings"]
    assert result["macro_score"]["warnings"]
    assert result["portfolio_fit_score"]["warnings"]


@pytest.mark.asyncio
async def test_build_asset_score_uses_candidate_portfolio_fit_when_available():
    with patch(
        "app.services.scoring_engine.market_data_service.get_quote",
        new_callable=AsyncMock,
        return_value={"symbol": "MSFT", "name": "Microsoft", "price": 420.0, "change_percent": 0.8, "currency": "USD"},
    ), patch(
        "app.services.scoring_engine.market_data_service.get_history",
        new_callable=AsyncMock,
        return_value=_history(),
    ), patch(
        "app.services.scoring_engine.get_fundamentals",
        new_callable=AsyncMock,
        return_value=_fundamentals(),
    ), patch(
        "app.services.scoring_engine.get_enhanced_sentiment",
        new_callable=AsyncMock,
        return_value=_sentiment(),
    ), patch(
        "app.services.scoring_engine.get_all_macro_indicators",
        new_callable=AsyncMock,
        return_value=_macro(),
    ), patch(
        "app.services.scoring_engine._portfolio_positions",
        new_callable=AsyncMock,
        return_value=[{"symbol": "AAPL", "name": "Apple", "type": "stock", "current_value": 10_000.0}],
    ), patch(
        "app.services.scoring_engine.build_portfolio_intelligence",
        new_callable=AsyncMock,
        return_value={
            "holdings_count": 1,
            "allocation": [{"symbol": "AAPL", "weight": 1.0}],
            "candidate_impact": {
                "symbol": "MSFT",
                "correlation_to_portfolio": 0.18,
                "volatility_delta": -0.012,
                "sharpe_delta": 0.09,
            },
        },
    ):
        result = await build_asset_score("MSFT", user_id="test-user", tenant_id="default")

    assert result["portfolio_context"]["available"] is True
    assert result["portfolio_fit_score"]["value"] > 55
