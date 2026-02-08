"""Alerts engine that combines multi-factor alert scanning with Telegram delivery.

Orchestrates the full alert pipeline:
1. Scan assets using the alert scorer
2. Filter by severity threshold
3. Deliver qualifying alerts via Telegram
4. Return results summary
"""

import logging

from app.schemas.asset import Alert, AlertSeverity
from app.services.alert_scorer import scan_symbols
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


def _meets_threshold(alert: Alert, min_severity: AlertSeverity) -> bool:
    """Check if alert severity meets the minimum threshold."""
    return SEVERITY_ORDER.get(alert.severity, 0) >= SEVERITY_ORDER.get(min_severity, 0)


async def scan_and_notify(
    symbols: list[dict],
    min_severity: str = "high",
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
    alerts = await scan_symbols(symbols)

    # Determine threshold
    threshold = MIN_SEVERITY_FOR_NOTIFY.get(min_severity, AlertSeverity.HIGH)

    # Filter alerts that meet the notification threshold
    notify_alerts = [a for a in alerts if _meets_threshold(a, threshold)]

    # Deliver via Telegram
    notified: list[dict] = []
    telegram_ok = telegram_service.configured

    if telegram_ok and notify_alerts:
        for alert in notify_alerts:
            alert_dict = {
                "title": alert.title,
                "description": alert.description,
                "severity": alert.severity.value,
                "asset_symbol": alert.asset_symbol or "",
                "suggested_action": alert.suggested_action.value,
                "confidence": alert.confidence,
            }
            result = await telegram_service.send_alert(alert_dict)
            notified.append({
                "alert_id": alert.id,
                "symbol": alert.asset_symbol,
                "title": alert.title,
                "severity": alert.severity.value,
                "delivered": result is not None,
            })

    return {
        "alerts": alerts,
        "notified": notified,
        "total_alerts": len(alerts),
        "total_notified": len([n for n in notified if n["delivered"]]),
        "telegram_configured": telegram_ok,
    }
