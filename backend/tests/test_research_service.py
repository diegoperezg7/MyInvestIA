from datetime import datetime, timedelta, timezone

import pytest

from app.services import research_service
from app.services.store import store


def test_build_backtest_lite_compares_snapshot_against_latest_prices():
    latest_ts = datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc)
    base_snapshot = {
        "id": "snap-old",
        "captured_at": (latest_ts - timedelta(days=8)).isoformat(),
        "rankings": [
            {"symbol": "AAPL", "reference_price": 100.0, "current_price": 100.0},
            {"symbol": "MSFT", "reference_price": 200.0, "current_price": 200.0},
        ],
    }
    latest_snapshot = {
        "id": "snap-latest",
        "captured_at": latest_ts.isoformat(),
        "rankings": [
            {"symbol": "AAPL", "reference_price": 110.0, "current_price": 110.0},
            {"symbol": "MSFT", "reference_price": 180.0, "current_price": 180.0},
        ],
    }

    validation = research_service._build_backtest_lite(base_snapshot, latest_snapshot)

    assert validation == [
        {
            "horizon": "1W",
            "average_return": 0.0,
            "median_return": 0.0,
            "hit_rate": 0.5,
            "samples": 2,
        }
    ]


@pytest.mark.asyncio
async def test_list_snapshots_recomputes_validation_from_latest_snapshot(monkeypatch):
    now = datetime.now(timezone.utc)
    older_snapshot = store.save_research_snapshot(
        "test-user",
        {
            "id": "snap-older",
            "name": "Snapshot older",
            "universe": ["AAPL"],
            "rankings": [
                {"symbol": "AAPL", "reference_price": 100.0, "current_price": 100.0}
            ],
            "validation": [],
            "captured_at": (now - timedelta(days=8)).isoformat(),
        },
        "default",
    )
    latest_snapshot = store.save_research_snapshot(
        "test-user",
        {
            "id": "snap-latest",
            "name": "Snapshot latest",
            "universe": ["AAPL"],
            "rankings": [
                {"symbol": "AAPL", "reference_price": 115.0, "current_price": 115.0}
            ],
            "validation": [],
            "captured_at": now.isoformat(),
        },
        "default",
    )

    payload = research_service.list_snapshots("test-user", "default")
    snapshots = {snapshot["id"]: snapshot for snapshot in payload["snapshots"]}

    assert snapshots[older_snapshot["id"]]["validation"] == [
        {
            "horizon": "1W",
            "average_return": 0.15,
            "median_return": 0.15,
            "hit_rate": 1.0,
            "samples": 1,
        }
    ]
    assert snapshots[latest_snapshot["id"]]["validation"] == []


@pytest.mark.asyncio
async def test_get_rankings_saves_new_snapshot_without_stale_validation(monkeypatch):
    now = datetime.now(timezone.utc)
    store.save_research_snapshot(
        "test-user",
        {
            "id": "snap-older",
            "name": "Snapshot older",
            "universe": ["AAPL"],
            "rankings": [
                {"symbol": "AAPL", "reference_price": 100.0, "current_price": 100.0}
            ],
            "validation": [],
            "captured_at": (now - timedelta(days=8)).isoformat(),
        },
        "default",
    )

    monkeypatch.setattr(research_service, "_resolve_universe", lambda *args, **kwargs: ["AAPL"])

    async def fake_macro_indicators():
        return []

    async def fake_symbol_research(symbol: str, macro_indicators: list[dict]):
        return {
            "symbol": symbol,
            "name": "Apple Inc.",
            "quote": {"price": 120.0},
            "factors_v1": {"momentum": 75.0},
            "quant_scores": {"confidence": 0.81, "verdict": "buy"},
            "composite_score_v1": 75.0,
            "thesis_id": None,
            "inbox_item_id": None,
        }

    monkeypatch.setattr(research_service, "get_all_macro_indicators", fake_macro_indicators)
    monkeypatch.setattr(research_service, "_build_symbol_research", fake_symbol_research)

    payload = await research_service.get_rankings(
        "test-user",
        "default",
        save_snapshot=True,
    )
    snapshots = store.get_research_snapshots("test-user", "default")

    assert payload["snapshot_id"] == snapshots[0]["id"]
    assert snapshots[0]["validation"] == []
