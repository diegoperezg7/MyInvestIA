"""Structured alerting schemas with traceability fields."""

from pydantic import BaseModel, Field

from app.schemas.asset import AlertSeverity, AlertType, SuggestedAction


class AlertEvidence(BaseModel):
    category: str
    summary: str = ""
    value: float | str | int | None = None
    source: str = ""
    timestamp: str = ""


class StructuredAlert(BaseModel):
    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    reasoning: str
    reason: str = ""
    evidence: list[AlertEvidence] = Field(default_factory=list)
    confidence: float = 0.0
    suggested_action: SuggestedAction
    created_at: str
    asset_symbol: str | None = None
    sources: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class StructuredAlertList(BaseModel):
    alerts: list[StructuredAlert] = Field(default_factory=list)
    total: int = 0


class NotifiedAlert(BaseModel):
    alert_id: str
    symbol: str | None = None
    title: str
    severity: str
    delivered: bool
    sources: list[str] = Field(default_factory=list)


class StructuredScanAndNotifyResponse(BaseModel):
    alerts: list[StructuredAlert] = Field(default_factory=list)
    notified: list[NotifiedAlert] = Field(default_factory=list)
    total_alerts: int = 0
    total_notified: int = 0
    telegram_configured: bool = False
