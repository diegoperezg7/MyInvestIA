"""Alerts engine that combines structured alert scanning with Telegram delivery."""

import logging

from app.schemas.alerting import StructuredAlert
from app.schemas.asset import AlertSeverity
from app.services.alert_scorer import build_portfolio_alerts, scan_symbols, sort_alerts
from app.services.telegram_service import telegram_service

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {
    AlertSeverity.LOW: 0,
    AlertSeverity.MEDIUM: 1,
    AlertSeverity.HIGH: 2,
    AlertSeverity.CRITICAL: 3,
}

MIN_SEVERITY_FOR_NOTIFY = {
    "all": AlertSeverity.LOW,
    "medium": AlertSeverity.MEDIUM,
    "high": AlertSeverity.HIGH,
    "critical": AlertSeverity.CRITICAL,
}


def _meets_threshold(alert: StructuredAlert, min_severity: AlertSeverity) -> bool:
    """Check if alert severity meets the minimum threshold."""
    return SEVERITY_ORDER.get(alert.severity, 0) >= SEVERITY_ORDER.get(min_severity, 0)


async def scan_and_notify(
    symbols: list[dict],
    min_severity: str = "high",
    chat_id: str | None = None,
    portfolio_holdings: list[dict] | None = None,
) -> dict:
    """Scan symbols for alerts and deliver qualifying ones via Telegram.

    Args:
        symbols: List of {"symbol": str, "type": str} dicts to scan
        min_severity: Minimum severity to trigger Telegram notification
                     ("all", "medium", "high", "critical")

    Returns:
        Dict with: alerts (all found), notified (sent to Telegram),
                   total_alerts, total_notified, telegram_configured
    """
    # Run the scan
    asset_alerts = await scan_symbols(symbols)
    portfolio_alerts = await build_portfolio_alerts(portfolio_holdings or [])
    alerts = sort_alerts(asset_alerts + portfolio_alerts)

    # Determine threshold
    threshold = MIN_SEVERITY_FOR_NOTIFY.get(min_severity, AlertSeverity.HIGH)

    # Filter alerts that meet the notification threshold
    notify_alerts = [a for a in alerts if _meets_threshold(a, threshold)]

    # Deliver via Telegram (personal bot chat if available, otherwise legacy global chat)
    notified: list[dict] = []
    telegram_ok = bool(chat_id) or telegram_service.configured

    if telegram_ok and notify_alerts:
        for alert in notify_alerts:
            reason = getattr(alert, "reason", "") or getattr(alert, "reasoning", "")
            sources = list(getattr(alert, "sources", []) or [])
            warnings = list(getattr(alert, "warnings", []) or [])
            evidence = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in list(getattr(alert, "evidence", []) or [])
            ]
            alert_dict = {
                "title": alert.title,
                "description": alert.description,
                "reason": reason,
                "reasoning": alert.reasoning,
                "severity": alert.severity.value,
                "asset_symbol": alert.asset_symbol or "",
                "suggested_action": alert.suggested_action.value,
                "confidence": alert.confidence,
                "sources": sources,
                "warnings": warnings,
                "evidence": evidence,
            }
            if chat_id:
                result = await telegram_service.send_alert_to_chat(chat_id, alert_dict)
            else:
                result = await telegram_service.send_alert(alert_dict)
            notified.append({
                "alert_id": alert.id,
                "symbol": alert.asset_symbol,
                "title": alert.title,
                "severity": alert.severity.value,
                "delivered": result is not None,
                "sources": sources,
            })

    return {
        "alerts": alerts,
        "notified": notified,
        "total_alerts": len(alerts),
        "total_notified": len([n for n in notified if n["delivered"]]),
        "telegram_configured": telegram_ok,
    }
