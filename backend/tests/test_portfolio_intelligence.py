import pytest

from app.services.portfolio_intelligence import analyze_portfolio_from_data


def _history_from_prices(prices: list[float]) -> list[dict]:
    rows = []
    for index, close in enumerate(prices):
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


def test_analyze_portfolio_from_data_builds_risk_and_rebalance_views():
    holdings = [
        {"symbol": "AAPL", "name": "Apple", "type": "stock", "current_value": 7000.0},
        {"symbol": "MSFT", "name": "Microsoft", "type": "stock", "current_value": 3000.0},
    ]
    histories = {
        "AAPL": _history_from_prices([100 + i * 0.8 for i in range(120)]),
        "MSFT": _history_from_prices([90 + i * 0.4 + ((i % 5) - 2) * 0.3 for i in range(120)]),
    }
    metadata = {
        "AAPL": {"sector": "Technology", "currency": "USD", "country": "United States"},
        "MSFT": {"sector": "Technology", "currency": "USD", "country": "United States"},
    }
    benchmark = _history_from_prices([95 + i * 0.5 for i in range(120)])
    candidate_history = _history_from_prices([80 + i * 0.2 + ((i % 7) - 3) * 0.5 for i in range(120)])

    result = analyze_portfolio_from_data(
        holdings,
        histories,
        metadata,
        benchmark_history=benchmark,
        candidate_symbol="TLT",
        candidate_weight=0.10,
        candidate_history=candidate_history,
        candidate_metadata={"sector": "Rate Sensitive", "currency": "USD", "country": "United States"},
    )

    assert result["total_value"] == 10000.0
    assert result["holdings_count"] == 2
    assert result["risk_metrics"]["annualized_volatility"] > 0
    assert result["risk_metrics"]["sharpe_ratio"] != 0
    assert result["concentration"]["asset"]["top_weight"] == pytest.approx(0.7, abs=1e-6)
    assert result["rebalance_suggestions"]
    assert result["candidate_impact"] is not None
    assert result["candidate_impact"]["symbol"] == "TLT"
    assert len(result["strategy_snapshots"]) == 4
    risk_share_sum = sum(item["risk_share"] for item in result["contribution_to_risk"])
    assert risk_share_sum == pytest.approx(1.0, abs=1e-5)


def test_analyze_portfolio_from_data_reports_missing_history():
    holdings = [
        {"symbol": "AAPL", "name": "Apple", "type": "stock", "current_value": 5000.0},
    ]
    histories = {"AAPL": []}
    metadata = {"AAPL": {"sector": "Technology", "currency": "USD", "country": "United States"}}

    result = analyze_portfolio_from_data(holdings, histories, metadata)

    assert result["warnings"]
    assert result["correlation"]["symbols"] == []
    assert result["candidate_impact"] is None
