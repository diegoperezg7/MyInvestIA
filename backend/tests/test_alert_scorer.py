"""Tests for the alert_scorer module."""

from app.schemas.asset import AlertSeverity, AlertType, SuggestedAction
from app.services.alert_scorer import (
    _price_move_alert,
    _technical_alerts,
    _contextual_alerts,
    _filing_alerts,
    score_asset,
    sort_alerts,
    _make_alert,
    _polarity,
    SEVERITY_ORDER,
)


def test_severity_order_ranking():
    assert SEVERITY_ORDER[AlertSeverity.CRITICAL] < SEVERITY_ORDER[AlertSeverity.HIGH]
    assert SEVERITY_ORDER[AlertSeverity.HIGH] < SEVERITY_ORDER[AlertSeverity.MEDIUM]
    assert SEVERITY_ORDER[AlertSeverity.MEDIUM] < SEVERITY_ORDER[AlertSeverity.LOW]


def test_polarity_bullish():
    assert _polarity(0.5) == "bullish"
    assert _polarity(0.2) == "bullish"


def test_polarity_bearish():
    assert _polarity(-0.5) == "bearish"
    assert _polarity(-0.2) == "bearish"


def test_polarity_neutral():
    assert _polarity(0.0) == "neutral"
    assert _polarity(0.1) == "neutral"
    assert _polarity(-0.1) == "neutral"


def test_price_move_alert_spike_triggers_alert():
    quote = {"price": 150.0, "change_percent": 6.5}
    alerts = _price_move_alert("AAPL", quote)
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.MEDIUM
    assert "surging" in alerts[0].title.lower()


def test_price_move_alert_extreme_spike_triggers_high():
    quote = {"price": 150.0, "change_percent": 9.0}
    alerts = _price_move_alert("AAPL", quote)
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.HIGH


def test_price_move_alert_drop_triggers_alert():
    quote = {"price": 140.0, "change_percent": -6.5}
    alerts = _price_move_alert("AAPL", quote)
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.MEDIUM
    assert "dropping" in alerts[0].title.lower()


def test_price_move_alert_extreme_drop_triggers_high():
    quote = {"price": 130.0, "change_percent": -9.0}
    alerts = _price_move_alert("AAPL", quote)
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.HIGH


def test_price_move_alert_no_move_no_alert():
    quote = {"price": 145.0, "change_percent": 0.5}
    alerts = _price_move_alert("AAPL", quote)
    assert len(alerts) == 0


def test_technical_alerts_rsi_extreme_oversold():
    indicators = {"rsi": {"value": 15.0}, "signal_counts": {}}
    alerts = _technical_alerts("AAPL", indicators)
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.HIGH
    assert alerts[0].suggested_action == SuggestedAction.BUY
    assert "oversold" in alerts[0].title.lower()


def test_technical_alerts_rsi_oversold():
    indicators = {"rsi": {"value": 25.0}, "signal_counts": {}}
    alerts = _technical_alerts("AAPL", indicators)
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.MEDIUM


def test_technical_alerts_rsi_extreme_overbought():
    indicators = {"rsi": {"value": 85.0}, "signal_counts": {}}
    alerts = _technical_alerts("AAPL", indicators)
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.HIGH
    assert alerts[0].suggested_action == SuggestedAction.SELL


def test_technical_alerts_rsi_overbought():
    indicators = {"rsi": {"value": 75.0}, "signal_counts": {}}
    alerts = _technical_alerts("AAPL", indicators)
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.MEDIUM


def test_technical_alerts_strong_bullish_convergence():
    indicators = {"signal_counts": {"bullish": 4, "bearish": 0}}
    alerts = _technical_alerts("AAPL", indicators)
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.HIGH
    assert alerts[0].suggested_action == SuggestedAction.BUY
    assert "bullish convergence" in alerts[0].title.lower()


def test_technical_alerts_strong_bearish_convergence():
    indicators = {"signal_counts": {"bullish": 0, "bearish": 4}}
    alerts = _technical_alerts("AAPL", indicators)
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.HIGH
    assert alerts[0].suggested_action == SuggestedAction.SELL
    assert "bearish convergence" in alerts[0].title.lower()


def test_technical_alerts_no_signals():
    indicators = {"signal_counts": {"bullish": 1, "bearish": 1}}
    alerts = _technical_alerts("AAPL", indicators)
    assert len(alerts) == 0


def test_contextual_alerts_bullish_breakout_with_sentiment():
    quote = {"change_percent": 5.0}
    indicators = {
        "overall_signal": "bullish",
        "signal_counts": {"bullish": 3, "bearish": 0},
    }
    sentiment = {
        "unified_score": 0.3,
        "coverage_confidence": 0.5,
        "recent_shift": 0.1,
        "warnings": [],
        "sources": [{"source_name": "news", "score": 0.3}],
    }
    alerts = _contextual_alerts("AAPL", quote, indicators, sentiment)
    assert len(alerts) >= 1
    breakout_alerts = [a for a in alerts if "breakout" in a.title.lower()]
    assert len(breakout_alerts) == 1
    assert breakout_alerts[0].severity == AlertSeverity.MEDIUM


def test_contextual_alerts_bearish_breakdown_with_sentiment():
    quote = {"change_percent": -5.0}
    indicators = {
        "overall_signal": "bearish",
        "signal_counts": {"bullish": 0, "bearish": 3},
    }
    sentiment = {
        "unified_score": -0.3,
        "coverage_confidence": 0.5,
        "recent_shift": -0.1,
        "warnings": [],
        "sources": [{"source_name": "news", "score": -0.3}],
    }
    alerts = _contextual_alerts("AAPL", quote, indicators, sentiment)
    breakdown_alerts = [a for a in alerts if "breakdown" in a.title.lower()]
    assert len(breakdown_alerts) == 1


def test_contextual_alerts_sentiment_shift():
    quote = {"change_percent": 0.5}
    indicators = {"overall_signal": "neutral", "signal_counts": {}}
    sentiment = {
        "unified_score": 0.1,
        "coverage_confidence": 0.4,
        "recent_shift": 0.4,
        "warnings": [],
        "sources": [{"source_name": "news", "score": 0.1}],
    }
    alerts = _contextual_alerts("AAPL", quote, indicators, sentiment)
    shift_alerts = [
        a
        for a in alerts
        if "sentiment" in a.title.lower() and "shift" in a.title.lower()
    ]
    assert len(shift_alerts) == 1


def test_contextual_alerts_contradictory_signals():
    quote = {"change_percent": 0.5}
    indicators = {
        "overall_signal": "bullish",
        "signal_counts": {"bullish": 3, "bearish": 0},
    }
    sentiment = {
        "unified_score": -0.4,
        "coverage_confidence": 0.5,
        "recent_shift": 0.0,
        "warnings": [],
        "sources": [],
        "divergences": [],
    }
    alerts = _contextual_alerts("AAPL", quote, indicators, sentiment)
    contradictory_alerts = [a for a in alerts if "contradictory" in a.title.lower()]
    assert len(contradictory_alerts) == 1


def test_contextual_alerts_missing_context_returns_empty():
    alerts = _contextual_alerts("AAPL", None, None, None)
    assert len(alerts) == 0


def test_filing_alerts_recent_8k():
    filings = {
        "filings": [
            {
                "form": "8-K",
                "filed_at": "2025-01-01T00:00:00Z",
                "description": "Material event",
                "items": "Item 8.01",
            }
        ]
    }
    alerts = _filing_alerts("AAPL", filings)
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.HIGH


def test_filing_alerts_recent_10q():
    filings = {
        "filings": [
            {
                "form": "10-Q",
                "filed_at": "2025-01-01T00:00:00Z",
                "description": "Quarterly report",
                "items": "",
            }
        ]
    }
    alerts = _filing_alerts("AAPL", filings)
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.MEDIUM


def test_filing_alerts_old_filing_ignored():
    filings = {
        "filings": [
            {
                "form": "8-K",
                "filed_at": "2024-01-01T00:00:00Z",
                "description": "Old filing",
                "items": "",
            }
        ]
    }
    alerts = _filing_alerts("AAPL", filings)
    assert len(alerts) == 0


def test_filing_alerts_no_filings():
    alerts = _filing_alerts("AAPL", None)
    assert len(alerts) == 0


def test_filing_alerts_empty_list():
    alerts = _filing_alerts("AAPL", {"filings": []})
    assert len(alerts) == 0


def test_score_asset_combines_all_sources():
    quote = {"change_percent": 6.0}
    indicators = {"rsi": {"value": 80.0}, "signal_counts": {"bullish": 4}}
    sentiment = {
        "unified_score": 0.5,
        "coverage_confidence": 0.6,
        "recent_shift": 0.3,
        "warnings": [],
        "sources": [{"source_name": "news", "score": 0.5}],
    }
    filings = {"filings": []}
    alerts = score_asset("AAPL", quote, indicators, sentiment, filings)
    assert len(alerts) >= 3


def test_score_asset_deduplicates_by_title():
    quote = {"change_percent": 6.5}
    indicators = {"rsi": {"value": 80.0}, "signal_counts": {"bullish": 4}}
    sentiment = {
        "unified_score": 0.5,
        "coverage_confidence": 0.6,
        "recent_shift": 0.3,
        "warnings": [],
        "sources": [],
    }
    filings = None
    alerts = score_asset("AAPL", quote, indicators, sentiment, filings)
    titles = [a.title for a in alerts]
    assert len(titles) == len(set(titles))


def test_sort_alerts_by_severity():
    alerts = [
        _make_alert(
            AlertType.PRICE,
            AlertSeverity.LOW,
            "Low alert",
            "desc",
            "reason",
            0.5,
            SuggestedAction.MONITOR,
        ),
        _make_alert(
            AlertType.PRICE,
            AlertSeverity.HIGH,
            "High alert",
            "desc",
            "reason",
            0.5,
            SuggestedAction.MONITOR,
        ),
        _make_alert(
            AlertType.PRICE,
            AlertSeverity.MEDIUM,
            "Medium alert",
            "desc",
            "reason",
            0.5,
            SuggestedAction.MONITOR,
        ),
    ]
    sorted_alerts = sort_alerts(alerts)
    assert sorted_alerts[0].severity == AlertSeverity.HIGH
    assert sorted_alerts[1].severity == AlertSeverity.MEDIUM
    assert sorted_alerts[2].severity == AlertSeverity.LOW


def test_sort_alerts_by_confidence_within_severity():
    high_1 = _make_alert(
        AlertType.PRICE,
        AlertSeverity.HIGH,
        "High 1",
        "desc",
        "reason",
        0.3,
        SuggestedAction.MONITOR,
    )
    high_2 = _make_alert(
        AlertType.PRICE,
        AlertSeverity.HIGH,
        "High 2",
        "desc",
        "reason",
        0.8,
        SuggestedAction.MONITOR,
    )
    sorted_alerts = sort_alerts([high_1, high_2])
    assert sorted_alerts[0].confidence >= sorted_alerts[1].confidence


def test_make_alert_includes_evidence():
    alert = _make_alert(
        AlertType.PRICE,
        AlertSeverity.MEDIUM,
        "Test alert",
        "Description",
        "Reasoning",
        0.7,
        SuggestedAction.MONITOR,
        symbol="AAPL",
        evidence=[
            {
                "category": "price",
                "summary": "Move",
                "value": 5.0,
                "source": "market_data",
            }
        ],
    )
    assert alert.asset_symbol == "AAPL"
    assert len(alert.evidence) == 1
    assert alert.evidence[0].category == "price"


def test_make_alert_includes_warnings():
    alert = _make_alert(
        AlertType.PRICE,
        AlertSeverity.MEDIUM,
        "Test alert",
        "Description",
        "Reasoning",
        0.7,
        SuggestedAction.MONITOR,
        warnings=["Low coverage", "Single source"],
    )
    assert len(alert.warnings) == 2


def test_make_alert_includes_sources():
    alert = _make_alert(
        AlertType.PRICE,
        AlertSeverity.MEDIUM,
        "Test alert",
        "Description",
        "Reasoning",
        0.7,
        SuggestedAction.MONITOR,
        sources=["market_data", "technical_analysis"],
    )
    assert len(alert.sources) == 2


def test_score_asset_handles_missing_data_gracefully():
    alerts = score_asset("AAPL", None, None, None, None)
    assert isinstance(alerts, list)
    assert len(alerts) == 0
