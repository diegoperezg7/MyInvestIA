from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_market_score_route(client):
    payload = {
        "symbol": "AAPL",
        "asset_type": "stock",
        "quote": {"price": 200.0, "change_percent": 1.2, "name": "Apple", "currency": "USD"},
        "fundamentals_score": {"name": "fundamentals_score", "value": 72.0},
        "technical_score": {"name": "technical_score", "value": 68.0},
        "sentiment_score": {"name": "sentiment_score", "value": 61.0},
        "macro_score": {"name": "macro_score", "value": 55.0},
        "portfolio_fit_score": {"name": "portfolio_fit_score", "value": 50.0},
        "total_score": {"name": "total_score", "value": 63.4},
        "weights": {
            "fundamentals_score": 0.25,
            "technical_score": 0.25,
            "sentiment_score": 0.15,
            "macro_score": 0.15,
            "portfolio_fit_score": 0.20,
        },
        "quant_overlay": {},
        "portfolio_context": {"available": False},
        "generated_at": "2026-03-06T10:00:00+00:00",
        "decision_support_only": True,
        "disclaimer": "Informational scoring only.",
    }

    with patch("app.routers.market.build_asset_score", new=AsyncMock(return_value=payload)):
        response = await client.get("/api/v1/market/score/AAPL")

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["total_score"]["value"] == 63.4


@pytest.mark.asyncio
async def test_portfolio_intelligence_route(client, mock_market_data):
    payload = {
        "generated_at": "2026-03-06T10:00:00+00:00",
        "total_value": 1000.0,
        "holdings_count": 1,
        "allocation": [
            {
                "symbol": "AAPL",
                "name": "Apple",
                "type": "stock",
                "weight": 1.0,
                "current_value": 1000.0,
                "sector": "Technology",
                "currency": "USD",
            }
        ],
        "concentration": {
            "asset": {"items": [{"key": "AAPL", "weight": 1.0, "value": 1000.0}], "top_weight": 1.0, "hhi_score": 1.0, "alerts": []},
            "sector": {"items": [{"key": "Technology", "weight": 1.0, "value": 1000.0}], "top_weight": 1.0, "hhi_score": 1.0, "alerts": []},
            "currency": {"items": [{"key": "USD", "weight": 1.0, "value": 1000.0}], "top_weight": 1.0, "hhi_score": 1.0, "alerts": []},
        },
        "risk_metrics": {},
        "correlation": {"symbols": ["AAPL"], "matrix": [[1.0]], "average_pairwise_correlation": 0.0, "high_correlations": []},
        "rolling_metrics": {},
        "contribution_to_risk": [],
        "strategy_snapshots": [],
        "rebalance_suggestions": [],
        "candidate_impact": None,
        "warnings": [],
        "disclaimer": "Informational only.",
    }

    mock_market_data.get_quote = AsyncMock(return_value={
        "symbol": "AAPL",
        "name": "Apple",
        "price": 100.0,
        "change_percent": 0.0,
        "volume": 10,
        "currency": "EUR",
    })

    await client.post("/api/v1/portfolio/", json={
        "symbol": "AAPL",
        "name": "Apple",
        "type": "stock",
        "quantity": 10,
        "avg_buy_price": 100.0,
    })

    with patch("app.routers.portfolio.build_portfolio_intelligence", new=AsyncMock(return_value=payload)):
        response = await client.get("/api/v1/portfolio/intelligence")

    assert response.status_code == 200
    data = response.json()
    assert data["holdings_count"] == 1
    assert data["allocation"][0]["symbol"] == "AAPL"
