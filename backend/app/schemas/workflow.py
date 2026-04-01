from enum import Enum

from pydantic import BaseModel, Field


class AssistantMode(str, Enum):
    PRUDENT = "prudent"
    BALANCED = "balanced"
    PROACTIVE = "proactive"


class InboxScope(str, Enum):
    PORTFOLIO = "portfolio"
    WATCHLIST = "watchlist"
    MACRO = "macro"
    RESEARCH = "research"


class InboxStatus(str, Enum):
    OPEN = "open"
    SAVED = "saved"
    DISMISSED = "dismissed"
    SNOOZED = "snoozed"
    DONE = "done"


class InsightState(str, Enum):
    CONFIRMED = "confirmed"
    EXPLORATORY = "exploratory"


class ImpactLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Horizon(str, Enum):
    IMMEDIATE = "immediate"
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class EvidenceItem(BaseModel):
    category: str
    source: str
    summary: str
    url: str | None = None
    confidence: float = 0.0
    score: float = 0.0


class SourceBreakdownItem(BaseModel):
    source: str
    count: int = 0
    weight: float = 0.0
    confidence: float = 0.0
    retrieval_mode: str = "unknown"


class InboxItem(BaseModel):
    id: str
    scope: InboxScope
    kind: str
    title: str
    summary: str
    why_now: str = ""
    symbols: list[str] = []
    primary_symbol: str | None = None
    priority_score: float = 0.0
    confidence: float = 0.0
    impact: ImpactLevel = ImpactLevel.MEDIUM
    horizon: Horizon = Horizon.SHORT
    status: InboxStatus = InboxStatus.OPEN
    state: InsightState = InsightState.EXPLORATORY
    assistant_mode: AssistantMode = AssistantMode.BALANCED
    evidence: list[EvidenceItem] = []
    source_breakdown: list[SourceBreakdownItem] = []
    created_at: str = ""
    updated_at: str = ""
    expires_at: str = ""
    linked_thesis_id: str | None = None


class InboxResponse(BaseModel):
    items: list[InboxItem] = []
    total: int = 0
    generated_at: str = ""
    cached_until: str = ""


class InboxRefreshResponse(BaseModel):
    items: list[InboxItem] = []
    total: int = 0
    generated_at: str = ""
    cached_until: str = ""
    refreshed: bool = True


class InboxActionRequest(BaseModel):
    action: str = Field(pattern=r"^(save|dismiss|snooze|done|link_thesis)$")
    thesis_id: str | None = None


class ThesisStance(str, Enum):
    BULL = "bull"
    BASE = "base"
    BEAR = "bear"


class ThesisLifecycleStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class ThesisReviewState(str, Enum):
    VALIDATING = "validating"
    AT_RISK = "at_risk"
    BROKEN = "broken"


class ThesisBase(BaseModel):
    symbol: str
    stance: ThesisStance = ThesisStance.BASE
    conviction: float = Field(default=0.5, ge=0.0, le=1.0)
    horizon: Horizon = Horizon.MEDIUM
    entry_zone: str = ""
    invalidation: str = ""
    catalysts: list[str] = []
    risks: list[str] = []
    notes: str = ""


class ThesisCreateRequest(ThesisBase):
    inbox_item_id: str | None = None


class ThesisUpdateRequest(BaseModel):
    stance: ThesisStance | None = None
    conviction: float | None = Field(default=None, ge=0.0, le=1.0)
    horizon: Horizon | None = None
    entry_zone: str | None = None
    invalidation: str | None = None
    catalysts: list[str] | None = None
    risks: list[str] | None = None
    notes: str | None = None
    status: ThesisLifecycleStatus | None = None
    review_state: ThesisReviewState | None = None


class Thesis(BaseModel):
    id: str
    symbol: str
    stance: ThesisStance = ThesisStance.BASE
    conviction: float = 0.5
    horizon: Horizon = Horizon.MEDIUM
    entry_zone: str = ""
    invalidation: str = ""
    catalysts: list[str] = []
    risks: list[str] = []
    notes: str = ""
    status: ThesisLifecycleStatus = ThesisLifecycleStatus.ACTIVE
    review_state: ThesisReviewState = ThesisReviewState.VALIDATING
    linked_inbox_ids: list[str] = []
    created_at: str = ""
    updated_at: str = ""


class ThesisEvent(BaseModel):
    id: str
    thesis_id: str
    event_type: str
    summary: str
    review_state: ThesisReviewState | None = None
    metadata: dict = {}
    created_at: str = ""


class ThesisListResponse(BaseModel):
    theses: list[Thesis] = []
    total: int = 0


class ThesisReviewRequest(BaseModel):
    notes: str = ""


class ThesisReviewResponse(BaseModel):
    thesis: Thesis
    event: ThesisEvent
    supporting_items: list[InboxItem] = []


class EventItem(BaseModel):
    id: str
    event_type: str
    title: str
    description: str
    symbol: str | None = None
    event_at: str = ""
    importance: ImpactLevel = ImpactLevel.MEDIUM
    source: str = ""
    url: str | None = None
    metadata: dict = {}


class AlertCondition(BaseModel):
    field: str
    operator: str = Field(pattern=r"^(gt|gte|lt|lte|eq|contains)$")
    value: str
    source: str = ""


class AlertRuleCreateRequest(BaseModel):
    name: str
    symbols: list[str] = []
    conditions: list[AlertCondition] = []
    cooldown_minutes: int = Field(default=60, ge=0)
    delivery_channels: list[str] = ["telegram"]
    linked_thesis_id: str | None = None
    active: bool = True


class AlertRuleUpdateRequest(BaseModel):
    name: str | None = None
    symbols: list[str] | None = None
    conditions: list[AlertCondition] | None = None
    cooldown_minutes: int | None = Field(default=None, ge=0)
    delivery_channels: list[str] | None = None
    linked_thesis_id: str | None = None
    active: bool | None = None
    last_triggered_at: str | None = None


class CompoundAlertRule(BaseModel):
    id: str
    name: str
    symbols: list[str] = []
    conditions: list[AlertCondition] = []
    cooldown_minutes: int = 60
    delivery_channels: list[str] = ["telegram"]
    linked_thesis_id: str | None = None
    active: bool = True
    last_triggered_at: str | None = None
    created_at: str = ""
    updated_at: str = ""


class AlertRuleListResponse(BaseModel):
    rules: list[CompoundAlertRule] = []
    total: int = 0


class FactorSet(BaseModel):
    momentum: float = 0.0
    quality: float = 0.0
    value: float = 0.0
    revisions: float = 0.0
    sentiment: float = 0.0
    insider_accumulation: float = 0.0
    risk: float = 0.0


class ResearchRankingEntry(BaseModel):
    symbol: str
    name: str = ""
    composite_score: float = 0.0
    confidence: float = 0.0
    verdict: str = "neutral"
    factors: FactorSet = FactorSet()
    thesis_id: str | None = None
    inbox_item_id: str | None = None


class ResearchFactorResponse(BaseModel):
    symbol: str
    generated_at: str = ""
    composite_score: float = 0.0
    confidence: float = 0.0
    verdict: str = "neutral"
    regime: str = "unknown"
    adx: float = 0.0
    weights: dict[str, float] = {}
    factors: dict[str, float] = {}
    support_resistance: dict = {}
    candlestick_patterns: list[str] = []
    risk_metrics: dict = {}
    factor_agreement: float = 0.0


class BacktestLiteResult(BaseModel):
    horizon: str
    average_return: float = 0.0
    median_return: float = 0.0
    hit_rate: float = 0.0
    samples: int = 0


class ResearchScreen(BaseModel):
    id: str
    name: str
    symbols: list[str] = []
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""


class ResearchScreenRequest(BaseModel):
    name: str
    symbols: list[str] = []
    notes: str = ""


class ResearchSnapshot(BaseModel):
    id: str
    name: str = ""
    universe: list[str] = []
    rankings: list[ResearchRankingEntry] = []
    validation: list[BacktestLiteResult] = []
    captured_at: str = ""


class ResearchRankingsResponse(BaseModel):
    rankings: list[ResearchRankingEntry] = []
    universe: list[str] = []
    generated_at: str = ""
    snapshot_id: str | None = None
    screens: list[ResearchScreen] = []


class ResearchSnapshotListResponse(BaseModel):
    snapshots: list[ResearchSnapshot] = []
    total: int = 0


class BriefingResponse(BaseModel):
    briefing: str
    suggestions: list[str] = []
    generated_at: str = ""
    preset: str = "default"
    top_inbox_items: list[InboxItem] = []
    next_events: list[EventItem] = []
    thesis_watch: list[Thesis] = []
