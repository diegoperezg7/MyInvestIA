"""Schemas for portfolio intelligence analytics."""

from pydantic import BaseModel, Field


class PortfolioAllocationItem(BaseModel):
    symbol: str
    name: str = ""
    type: str = "stock"
    weight: float = 0.0
    current_value: float = 0.0
    sector: str = ""
    currency: str = "USD"


class PortfolioConcentrationBucket(BaseModel):
    key: str
    weight: float = 0.0
    value: float = 0.0


class PortfolioConcentrationSummary(BaseModel):
    items: list[PortfolioConcentrationBucket] = Field(default_factory=list)
    top_weight: float = 0.0
    hhi_score: float = 0.0
    alerts: list[str] = Field(default_factory=list)


class PortfolioRiskMetricsExtended(BaseModel):
    annualized_return: float = 0.0
    annualized_volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    beta: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    daily_return_mean: float = 0.0


class RollingMetricSummary(BaseModel):
    latest: float = 0.0
    average: float = 0.0
    minimum: float = 0.0
    maximum: float = 0.0
    samples: int = 0


class ContributionToRiskItem(BaseModel):
    symbol: str
    portfolio_weight: float = 0.0
    risk_contribution: float = 0.0
    risk_share: float = 0.0


class InformativeSuggestion(BaseModel):
    type: str
    priority: str = "medium"
    title: str
    summary: str = ""
    action: str = ""


class StrategyTargetWeight(BaseModel):
    symbol: str
    weight: float = 0.0


class StrategySnapshot(BaseModel):
    name: str
    description: str = ""
    target_weights: list[StrategyTargetWeight] = Field(default_factory=list)
    expected_return: float = 0.0
    expected_volatility: float = 0.0
    expected_sharpe: float = 0.0


class CandidateImpactResponse(BaseModel):
    symbol: str
    candidate_weight: float = 0.0
    candidate_sector: str = ""
    correlation_to_portfolio: float = 0.0
    volatility_delta: float = 0.0
    sharpe_delta: float = 0.0
    max_drawdown_delta: float = 0.0
    sector_exposure_before: list[PortfolioConcentrationBucket] = Field(default_factory=list)
    sector_exposure_after: list[PortfolioConcentrationBucket] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class PortfolioCorrelationResponse(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    matrix: list[list[float]] = Field(default_factory=list)
    average_pairwise_correlation: float = 0.0
    high_correlations: list[dict] = Field(default_factory=list)


class PortfolioIntelligenceResponse(BaseModel):
    generated_at: str = ""
    total_value: float = 0.0
    holdings_count: int = 0
    allocation: list[PortfolioAllocationItem] = Field(default_factory=list)
    concentration: dict[str, PortfolioConcentrationSummary] = Field(default_factory=dict)
    risk_metrics: PortfolioRiskMetricsExtended = Field(default_factory=PortfolioRiskMetricsExtended)
    correlation: PortfolioCorrelationResponse = Field(default_factory=PortfolioCorrelationResponse)
    rolling_metrics: dict[str, RollingMetricSummary] = Field(default_factory=dict)
    contribution_to_risk: list[ContributionToRiskItem] = Field(default_factory=list)
    strategy_snapshots: list[StrategySnapshot] = Field(default_factory=list)
    rebalance_suggestions: list[InformativeSuggestion] = Field(default_factory=list)
    candidate_impact: CandidateImpactResponse | None = None
    warnings: list[str] = Field(default_factory=list)
    disclaimer: str = ""
