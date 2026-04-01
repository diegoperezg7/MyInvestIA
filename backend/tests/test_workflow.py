from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_inbox_route(client):
    payload = {
        "items": [
            {
                "id": "item-1",
                "scope": "portfolio",
                "kind": "risk_alert",
                "title": "Concentration risk on NVDA",
                "summary": "NVDA is oversized.",
                "why_now": "Position is above internal threshold.",
                "symbols": ["NVDA"],
                "primary_symbol": "NVDA",
                "priority_score": 88.0,
                "confidence": 0.82,
                "impact": "high",
                "horizon": "medium",
                "status": "open",
                "state": "confirmed",
                "assistant_mode": "balanced",
                "evidence": [],
                "source_breakdown": [],
                "created_at": "2026-03-06T10:00:00+00:00",
                "updated_at": "2026-03-06T10:00:00+00:00",
                "expires_at": "2026-03-06T10:10:00+00:00",
                "linked_thesis_id": None,
            }
        ],
        "total": 1,
        "generated_at": "2026-03-06T10:00:00+00:00",
        "cached_until": "2026-03-06T10:10:00+00:00",
    }

    with patch("app.routers.inbox.get_inbox", new=AsyncMock(return_value=payload)):
        response = await client.get("/api/v1/inbox/?scope=portfolio")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Concentration risk on NVDA"
    assert data["items"][0]["state"] == "confirmed"


@pytest.mark.asyncio
async def test_create_thesis_from_inbox_flow(client):
    from app.services.store import store

    store.replace_inbox_items(
        "test-user",
        [
            {
                "id": "item-123",
                "scope": "portfolio",
                "kind": "opportunity",
                "title": "NVDA setup improving",
                "summary": "Momentum and sentiment are improving.",
                "why_now": "High-quality trend confirmation.",
                "symbols": ["NVDA"],
                "primary_symbol": "NVDA",
                "priority_score": 76.0,
                "confidence": 0.8,
                "impact": "high",
                "horizon": "short",
                "status": "open",
                "state": "confirmed",
                "assistant_mode": "balanced",
                "evidence": [],
                "source_breakdown": [],
                "created_at": "2026-03-06T10:00:00+00:00",
                "updated_at": "2026-03-06T10:00:00+00:00",
                "expires_at": "2026-03-06T10:10:00+00:00",
                "linked_thesis_id": None,
            }
        ],
        "default",
    )

    response = await client.post("/api/v1/inbox/item-123/thesis")

    assert response.status_code == 200
    data = response.json()
    assert data["thesis"]["symbol"] == "NVDA"
    assert data["thesis"]["linked_inbox_ids"] == ["item-123"]

    stored_item = store.get_inbox_item("test-user", "item-123", "default")
    assert stored_item["linked_thesis_id"] == data["thesis"]["id"]


@pytest.mark.asyncio
async def test_alert_rules_crud(client):
    create_response = await client.post(
        "/api/v1/alerts/rules",
        json={
            "name": "NVDA monitor",
            "symbols": ["NVDA"],
            "conditions": [
                {"field": "symbol", "operator": "contains", "value": "NVDA", "source": "inbox"}
            ],
            "cooldown_minutes": 60,
            "delivery_channels": ["telegram"],
            "active": True,
        },
    )

    assert create_response.status_code == 200
    rule = create_response.json()
    assert rule["name"] == "NVDA monitor"

    patch_response = await client.patch(
        f"/api/v1/alerts/rules/{rule['id']}",
        json={"active": False},
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["active"] is False

    list_response = await client.get("/api/v1/alerts/rules")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1


@pytest.mark.asyncio
async def test_research_rankings_route(client):
    payload = {
        "rankings": [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "composite_score": 78.4,
                "confidence": 0.72,
                "verdict": "buy",
                "factors": {
                    "momentum": 76.0,
                    "quality": 82.0,
                    "value": 54.0,
                    "revisions": 68.0,
                    "sentiment": 62.0,
                    "insider_accumulation": 50.0,
                    "risk": 71.0,
                },
                "thesis_id": None,
                "inbox_item_id": None,
            }
        ],
        "universe": ["AAPL"],
        "generated_at": "2026-03-06T10:00:00+00:00",
        "snapshot_id": None,
        "screens": [],
    }

    with patch("app.routers.research.get_rankings", new=AsyncMock(return_value=payload)):
        response = await client.get("/api/v1/research/rankings")

    assert response.status_code == 200
    data = response.json()
    assert data["rankings"][0]["symbol"] == "AAPL"
    assert data["rankings"][0]["factors"]["quality"] == 82.0


@pytest.mark.asyncio
async def test_profile_includes_workflow_preferences(client):
    update_response = await client.put(
        "/api/v1/user/profile",
        json={
            "display_name": "Darce",
            "risk_tolerance": "moderate",
            "investment_horizon": "medium",
            "goals": ["Diversificación"],
            "preferred_currency": "EUR",
            "notification_frequency": "important",
            "notification_channels": ["telegram"],
            "language": "es",
            "theme": "dark",
            "assistant_mode": "balanced",
            "default_horizon": "medium",
            "inbox_scope_preference": "portfolio",
        },
    )

    assert update_response.status_code == 200

    summary_response = await client.get("/api/v1/user/profile/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["assistant_mode"] == "balanced"
    assert summary["inbox_scope_preference"] == "portfolio"


@pytest.mark.asyncio
async def test_portfolio_risk_extended_response(client):
    with patch("app.services.portfolio_risk.calculate_portfolio_risk", new=AsyncMock(return_value={
        "metrics": {
            "var_95": 100.0,
            "var_99": 200.0,
            "sharpe_ratio": 1.2,
            "sortino_ratio": 1.5,
            "beta": 1.1,
            "max_drawdown": 0.2,
            "annual_volatility": 0.3,
            "daily_return_mean": 0.001,
        },
        "concentration": {
            "positions": [{"symbol": "AAPL", "weight": 1.0, "value": 1000.0}],
            "top3_concentration": 1.0,
            "hhi_score": 1.0,
            "diversification_score": 0.0,
            "alerts": [],
        },
        "correlation": {"symbols": ["AAPL"], "matrix": [[1.0]], "high_correlations": []},
        "stress_tests": [],
        "sector_exposure": [{"key": "Technology", "weight": 1.0, "value": 1000.0}],
        "country_exposure": [{"key": "United States", "weight": 1.0, "value": 1000.0}],
        "currency_exposure": [{"key": "USD", "weight": 1.0, "value": 1000.0}],
        "factor_proxies": [{"name": "growth", "exposure": 0.8, "confidence": 0.7, "note": "proxy"}],
        "correlated_clusters": [],
        "scenario_results": [],
        "portfolio_value": 1000.0,
    })), patch("app.routers.portfolio.store.get_holdings", return_value=[{
        "symbol": "AAPL",
        "name": "Apple",
        "type": "stock",
        "quantity": 1,
        "avg_buy_price": 1000.0,
    }]), patch("app.routers.portfolio.market_data_service.get_quote", new=AsyncMock(return_value={
        "symbol": "AAPL",
        "name": "Apple",
        "price": 1000.0,
        "change_percent": 0.0,
        "volume": 10,
        "currency": "EUR",
    })), patch("app.routers.portfolio.convert_currency", new=AsyncMock(return_value={"rate": 1.0})):
        response = await client.get("/api/v1/portfolio/risk")

    assert response.status_code == 200
    data = response.json()
    assert data["sector_exposure"][0]["key"] == "Technology"
    assert data["factor_proxies"][0]["name"] == "growth"
