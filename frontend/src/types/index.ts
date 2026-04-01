export interface Asset {
  symbol: string;
  name: string;
  type: "stock" | "etf" | "crypto" | "commodity" | "prediction";
  price: number;
  change_percent: number;
  volume: number;
}

export interface PortfolioHolding {
  asset: Asset;
  quantity: number;
  avg_buy_price: number;
  current_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
  source?: string;
  connection_id?: string;
}

export interface Portfolio {
  total_value: number;
  daily_pnl: number;
  daily_pnl_percent: number;
  holdings: PortfolioHolding[];
}

export interface Watchlist {
  id: string;
  name: string;
  assets: Asset[];
}

export interface Alert {
  id: string;
  type: "price" | "technical" | "sentiment" | "macro" | "multi_factor";
  severity: "low" | "medium" | "high" | "critical";
  title: string;
  description: string;
  reasoning: string;
  confidence: number;
  suggested_action: "buy" | "sell" | "wait" | "monitor";
  created_at: string;
  asset_symbol?: string;
}

export interface SentimentData {
  score: number;
  label: "bullish" | "bearish" | "neutral";
  sources_count: number;
  narrative: string;
}

export interface MacroIndicator {
  name: string;
  value: number;
  trend: "up" | "down" | "stable";
  impact_description: string;
}

export interface WatchlistList {
  watchlists: Watchlist[];
  total: number;
}

export interface MarketOverview {
  sentiment_index: number;
  top_gainers: Asset[];
  top_losers: Asset[];
  macro_indicators: MacroIndicator[];
}

export interface AlertList {
  alerts: Alert[];
  total: number;
}

export interface AssetQuote {
  symbol: string;
  name: string;
  price: number;
  change_percent: number;
  volume: number;
  previous_close: number;
  market_cap: number;
}

export interface HistoricalDataPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface HistoricalData {
  symbol: string;
  period: string;
  interval: string;
  data: HistoricalDataPoint[];
}

export interface TechnicalAnalysis {
  symbol: string;
  rsi: { value: number | null; signal: string };
  macd: {
    macd_line: number | null;
    signal_line: number | null;
    histogram: number | null;
    signal: string;
  };
  sma: { sma_20: number | null; sma_50: number | null; signal: string };
  ema: { ema_12: number | null; ema_26: number | null; signal: string };
  bollinger_bands: {
    upper: number | null;
    middle: number | null;
    lower: number | null;
    bandwidth: number | null;
    signal: string;
  };
  overall_signal: string;
  signal_counts: { bullish: number; bearish: number; neutral: number };
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  response: string;
  model: string;
}

export interface AIAnalysis {
  symbol: string;
  summary: string;
  signal: string;
  confidence: number;
}

export interface AIStatus {
  configured: boolean;
  model: string;
}

export interface MacroIndicatorDetail {
  name: string;
  ticker: string;
  value: number;
  change_percent: number;
  previous_close: number;
  trend: "up" | "down" | "stable";
  impact_description: string;
  category: string;
}

export interface MacroSummary {
  environment: string;
  risk_level: string;
  key_signals: string[];
}

export interface DataSourceStatus {
  name: string;
  active: boolean;
  retrieval_mode: string;
  confidence: number;
  note: string;
}

export interface OfficialSeriesPoint {
  id: string;
  name: string;
  value: number | null;
  date: string;
  change_percent: number;
  unit: string;
  source: string;
}

export interface FearGreedIndex {
  value: number;
  classification: string;
  timestamp: string;
  source: string;
}

export interface MacroIntelligenceResponse {
  indicators: MacroIndicatorDetail[];
  summary: MacroSummary;
  sources: DataSourceStatus[];
  official_series: OfficialSeriesPoint[];
  fear_greed: FearGreedIndex | null;
}

export interface PriceUpdate {
  symbol: string;
  price: number;
  change_percent: number;
  volume: number;
}

export interface NotificationStatus {
  configured: boolean;
  bot_name: string | null;
  bot_username: string | null;
  chat_id: string | null;
}

export interface NotificationResponse {
  success: boolean;
  message: string;
}

export interface PersonalBotHistoryEntry {
  id: string;
  connection_id: string;
  started_at: string | null;
  completed_at: string | null;
  status: string;
  reason: string | null;
  summary: string | null;
  message_count: number;
  alert_count: number;
  fingerprint: string | null;
}

export interface PersonalBotStatus {
  available: boolean;
  enabled: boolean;
  connected: boolean;
  status: string;
  bot_name: string | null;
  bot_username: string | null;
  chat_id: string | null;
  chat_name: string | null;
  telegram_username: string | null;
  cadence_minutes: number;
  min_severity: "all" | "medium" | "high" | "critical";
  include_briefing: boolean;
  include_inbox: boolean;
  include_portfolio: boolean;
  include_watchlist: boolean;
  include_macro: boolean;
  include_news: boolean;
  include_theses: boolean;
  include_buy_sell: boolean;
  send_only_on_changes: boolean;
  provisioned_defaults: boolean;
  pending_code: string | null;
  pending_expires_at: string | null;
  connect_url: string | null;
  verified_at: string | null;
  last_run_at: string | null;
  last_delivery_at: string | null;
  last_test_at: string | null;
  last_error: string | null;
  last_reason: string | null;
  last_message_count: number;
  last_alert_count: number;
  history: PersonalBotHistoryEntry[];
}

export interface PersonalBotActionResponse {
  success: boolean;
  message: string;
  status: PersonalBotStatus;
}

export interface PersonalBotRunResponse {
  success: boolean;
  message: string;
  sent_messages: number;
  sent_alerts: number;
  alerts_generated: number;
  top_items: number;
  events: number;
  thesis_watch: number;
  skipped: boolean;
  status: PersonalBotStatus;
}

export interface PersonalBotProvisionResponse {
  success: boolean;
  created_rules: number;
  message: string;
  status: PersonalBotStatus;
}

export interface SentimentAnalysis {
  symbol: string;
  score: number;
  label: "bullish" | "bearish" | "neutral";
  sources_count: number;
  narrative: string;
  key_factors: string[];
}

export interface NotifiedAlert {
  alert_id: string;
  symbol: string | null;
  title: string;
  severity: string;
  delivered: boolean;
}

export interface ScanAndNotifyResponse {
  alerts: Alert[];
  notified: NotifiedAlert[];
  total_alerts: number;
  total_notified: number;
  telegram_configured: boolean;
}

// --- Signals ---

export interface StructuredSignal {
  direction: "strong_buy" | "buy" | "neutral" | "sell" | "strong_sell";
  confidence: number;
  source: string;
  reasoning: string;
}

export interface SignalSummary {
  symbol: string;
  overall: string;
  overall_confidence: number;
  oscillators_rating: string;
  oscillators_buy: number;
  oscillators_sell: number;
  oscillators_neutral: number;
  moving_averages_rating: string;
  moving_averages_buy: number;
  moving_averages_sell: number;
  moving_averages_neutral: number;
  signals: StructuredSignal[];
}

// --- Personas ---

export interface Persona {
  id: string;
  name: string;
  title: string;
  avatar: string;
  style: string;
  description: string;
}

// --- Pipeline ---

export interface PipelineStep {
  id: string;
  name: string;
  description: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  result: Record<string, unknown> | null;
  error: string | null;
  duration_ms: number | null;
}

export interface PipelineStatus {
  symbol: string;
  current_step: number;
  total_steps: number;
  steps: PipelineStep[];
  completed: boolean;
  final_analysis: string | null;
  signal: string;
  confidence: number;
}

// --- Paper Trading ---

export interface PaperPosition {
  symbol: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
}

export interface PaperAccount {
  id: string;
  name: string;
  balance: number;
  initial_balance: number;
  total_value: number;
  total_pnl: number;
  total_pnl_percent: number;
  positions: PaperPosition[];
  created_at: string;
}

export interface PaperTrade {
  id: string;
  symbol: string;
  side: "buy" | "sell";
  quantity: number;
  price: number;
  total: number;
  created_at: string;
}

// --- Transactions ---

export interface Transaction {
  id: string;
  symbol: string;
  type: "buy" | "sell" | "dividend";
  quantity: number;
  price: number;
  total: number;
  date: string;
  notes: string;
}

export interface CostBasis {
  symbol: string;
  total_shares: number;
  average_cost: number;
  total_invested: number;
  realized_pnl: number;
  transactions_count: number;
}

// --- Briefing & News ---

export interface BriefingData {
  briefing: string;
  suggestions: string[];
  generated_at: string;
  preset?: string;
  top_inbox_items?: InboxItem[];
  next_events?: EventItem[];
  thesis_watch?: Thesis[];
}

export interface NewsArticle {
  headline: string;
  summary: string;
  source: string;
  url: string;
  datetime: number;
  related: string;
}

export interface NewsResponse {
  articles: NewsArticle[];
  source: string;
  configured: boolean;
}

// --- AI Recommendations ---

export interface Recommendation {
  category:
    | "opportunity"
    | "risk_alert"
    | "rebalance"
    | "trend"
    | "macro_shift"
    | "social_signal"
    | "earnings_watch"
    | "sector_rotation";
  title: string;
  reasoning: string;
  confidence: number;
  tickers: string[];
  action: string;
  urgency: "low" | "medium" | "high";
  inbox_item_id?: string | null;
  why_now?: string;
  horizon?: "immediate" | "short" | "medium" | "long";
}

export interface RecommendationsResponse {
  market_mood: string;
  mood_score: number;
  recommendations: Recommendation[];
  generated_at: string;
}

// --- AI News Feed ---

export type SourceCategory = "news" | "social" | "blog";

export interface ArticleAIAnalysis {
  impact_score: number;
  affected_tickers: string[];
  sentiment: "positive" | "negative" | "neutral";
  urgency: "breaking" | "high" | "normal";
  brief_analysis: string;
}

export interface AnalyzedArticle {
  id: string;
  headline: string;
  summary: string;
  source: string;
  source_provider: string;
  source_category: SourceCategory;
  url: string;
  datetime: number;
  ai_analysis: ArticleAIAnalysis | null;
  // Social-specific fields
  author?: string;
  score?: number;
  num_comments?: number;
  sentiment_label?: string; // StockTwits: "Bullish" | "Bearish"
  sentiment_score: number;
  confidence: number;
  relevance_score: number;
  ticker_mentions: string[];
  source_reliability: number;
  duplicate_group: string;
  engagement: number;
  retrieval_mode: string;
}

export interface NewsFeedResponse {
  articles: AnalyzedArticle[];
  total: number;
  sources_active: Record<string, boolean>;
  category_counts: Record<SourceCategory, number>;
  generated_at: string;
  top_narratives: Array<{
    label: string;
    mentions: number;
    avg_sentiment: number;
    symbols: string[];
  }>;
  source_health: Record<
    string,
    {
      active: boolean;
      articles: number;
      avg_confidence: number;
      retrieval_mode: string;
      status: string;
    }
  >;
}

// --- Enhanced Sentiment ---

export interface EnhancedSentimentSource {
  source_name: string;
  score: number;
  weight: number;
  details: Record<string, unknown>;
}

export interface EnhancedSentimentResponse {
  symbol: string;
  unified_score: number;
  unified_label: "bullish" | "bearish" | "neutral";
  sources: EnhancedSentimentSource[];
  coverage_confidence: number;
  news_momentum: number;
  social_momentum: number;
  top_narratives: Array<{
    label: string;
    mentions: number;
    avg_sentiment: number;
    symbols: string[];
  }>;
  source_breakdown: Array<{
    provider: string;
    count: number;
    avg_sentiment: number;
    avg_confidence: number;
    retrieval_mode: string;
  }>;
  cross_source_divergence: number;
  source_health: Record<
    string,
    {
      active: boolean;
      articles: number;
      avg_confidence: number;
      retrieval_mode: string;
      status: string;
    }
  >;
  total_data_points: number;
  generated_at: string;
}

export interface FilingItem {
  form: string;
  filed_at: string;
  description: string;
  items: string;
  url: string;
  accession_number: string;
}

export interface FilingsResponse {
  symbol: string;
  company_name: string;
  cik: string;
  source: string;
  filings: FilingItem[];
  generated_at: string;
}

export interface InsiderTransaction {
  insider_name: string;
  relation: string;
  transaction_type: string;
  shares: number;
  share_price: number;
  value: number;
  filing_date: string;
  source: string;
  url?: string;
}

export interface InsiderActivityResponse {
  symbol: string;
  source: string;
  transactions: InsiderTransaction[];
  generated_at: string;
}

// --- Social Sentiment ---

export interface SocialPlatformData {
  mentions: number;
  positive_mentions: number;
  negative_mentions: number;
  positive_score: number;
  negative_score: number;
  score: number;
}

export interface SocialSentimentData {
  symbol: string;
  reddit: SocialPlatformData;
  twitter: SocialPlatformData;
  total_mentions: number;
  combined_score: number;
  buzz_level: "none" | "low" | "moderate" | "high" | "viral";
  sentiment_label: "bullish" | "bearish" | "neutral";
  configured: boolean;
}

// --- Quantitative Scoring ---

export interface QuantFactors {
  trend: number;
  mean_reversion: number;
  momentum: number;
  volume: number;
  support_resistance: number;
  candlestick: number;
  macro: number;
  sentiment: number;
}

export interface QuantRiskMetrics {
  sharpe_ratio: number;
  max_drawdown: number;
  historical_volatility: number;
}

export interface QuantSupportResistance {
  pivot?: number;
  s1?: number;
  s2?: number;
  r1?: number;
  r2?: number;
  nearest_support?: number;
  nearest_resistance?: number;
  fractal_supports?: number[];
  fractal_resistances?: number[];
}

export interface QuantScores {
  factors: QuantFactors;
  composite_score: number;
  verdict: string;
  confidence: number;
  regime: "trending" | "range_bound" | "unknown";
  adx: number;
  weights: Record<string, number>;
  risk_metrics: QuantRiskMetrics;
  support_resistance: QuantSupportResistance;
  candlestick_patterns: string[];
  risk_vol_score: number;
  factor_agreement: number;
}

// --- Prediction ---

export interface PredictionResponse {
  symbol: string;
  verdict: "strong_buy" | "buy" | "neutral" | "sell" | "strong_sell";
  confidence: number;
  technical_summary: {
    signal?: string;
    key_indicators?: string[];
    support?: string;
    resistance?: string;
  };
  sentiment_summary: {
    unified_score?: number;
    label?: string;
    key_factors?: string[];
    divergences?: string[];
  };
  macro_summary: {
    environment?: string;
    risk_level?: string;
    vix_regime?: string;
    impact_on_asset?: string;
  };
  news_summary: {
    headline_count?: number;
    overall_tone?: string;
    top_headlines?: string[];
    summary?: string;
  };
  social_summary: {
    buzz_level?: string;
    total_mentions?: number;
    trend?: string;
    summary?: string;
  };
  price_outlook: {
    short_term?: string;
    medium_term?: string;
    catalysts?: string[];
    risks?: string[];
  };
  ai_analysis: string;
  quant_scores?: QuantScores;
  generated_at: string;
}

// --- Volatility ---

export interface VolatilityData {
  symbol: string;
  historical_volatility: number;
  atr: number;
  atr_percent: number;
  rsi: number;
  bollinger_bandwidth: number;
  daily_range: { high: number; low: number; range_percent: number };
  weekly_range: { high: number; low: number; range_percent: number };
  current_price: number;
  volatility_rating: "low" | "moderate" | "high" | "extreme";
}

// --- Connections ---

export type ConnectionType = "exchange" | "wallet" | "broker" | "prediction";
export type ConnectionStatus = "pending" | "active" | "error" | "disconnected";
export type SyncStatus = "never" | "success" | "partial" | "failed";

export interface ConnectionSummary {
  id: string;
  type: ConnectionType;
  provider: string;
  label: string;
  status: ConnectionStatus;
  last_sync_at: string | null;
  last_sync_status: string | null;
  last_sync_error: string | null;
  sync_count: number;
  holdings_count: number;
  total_value: number;
  created_at: string | null;
}

export interface ConnectionDetail extends ConnectionSummary {
  metadata: Record<string, unknown>;
  wallet_address: string | null;
  chain: string | null;
  holdings: Record<string, unknown>[];
}

export interface ConnectionList {
  connections: ConnectionSummary[];
  total: number;
}

export interface SyncResult {
  connection_id: string;
  status: string;
  holdings_synced: number;
  holdings_added: number;
  holdings_updated: number;
  holdings_removed: number;
  duration_ms: number;
  error: string | null;
}

export interface TestConnectionResult {
  success: boolean;
  message: string;
  account_info: Record<string, unknown>;
}

export interface SupportedProvider {
  id: string;
  name: string;
  type: ConnectionType;
  description: string;
  fields_required: string[];
  logo_url: string | null;
}

// --- Fundamentals ---

export interface CompanyInfo {
  name: string;
  sector: string;
  industry: string;
  market_cap: number;
  employees: number | null;
  description: string;
  website: string;
  country: string;
}

export interface FinancialRatios {
  pe_trailing: number;
  pe_forward: number;
  price_to_book: number;
  price_to_sales: number;
  ev_to_ebitda: number;
  roe: number;
  debt_to_equity: number;
  current_ratio: number;
  profit_margins: number;
  operating_margins: number;
  gross_margins: number;
  dividend_yield: number;
  payout_ratio: number;
  beta: number;
}

export interface GrowthMetrics {
  revenue_growth: number;
  earnings_growth: number;
  revenue_history: { period: string; value: number }[];
  earnings_history: { period: string; value: number }[];
}

export interface PeerComparison {
  symbol: string;
  name: string;
  pe_trailing: number;
  price_to_book: number;
  roe: number;
  profit_margins: number;
  market_cap: number;
}

export interface FundamentalsResponse {
  symbol: string;
  company_info: CompanyInfo;
  ratios: FinancialRatios;
  growth: GrowthMetrics;
  peers: PeerComparison[];
}

// --- Economic Calendar ---

export interface EconomicEvent {
  date: string;
  time: string;
  event: string;
  country: string;
  impact: "low" | "medium" | "high";
  forecast: number | null;
  previous: number | null;
  actual: number | null;
}

export interface EarningsEvent {
  symbol: string;
  name: string;
  date: string;
  eps_estimate: number | null;
  eps_actual: number | null;
  revenue_estimate: number | null;
  revenue_actual: number | null;
}

export interface EconomicCalendarResponse {
  events: EconomicEvent[];
  earnings: EarningsEvent[];
  date_range: { start: string; end: string };
  sources: DataSourceStatus[];
}

// --- Portfolio Risk Analytics ---

export interface PortfolioRiskMetrics {
  var_95: number;
  var_99: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  beta: number;
  max_drawdown: number;
  annual_volatility: number;
  daily_return_mean: number;
}

export interface ConcentrationRisk {
  positions: { symbol: string; weight: number; value: number }[];
  top3_concentration: number;
  hhi_score: number;
  diversification_score: number;
  alerts: string[];
}

export interface CorrelationData {
  symbols: string[];
  matrix: number[][];
  high_correlations: { pair: string; value: number }[];
}

export interface StressTestScenario {
  name: string;
  description: string;
  market_drop: number;
  estimated_portfolio_loss: number;
  estimated_portfolio_loss_pct: number;
}

export interface ExposureItem {
  key: string;
  weight: number;
  value: number;
}

export interface FactorProxy {
  name: string;
  exposure: number;
  confidence: number;
  note: string;
}

export interface CorrelatedCluster {
  symbols: string[];
  average_correlation: number;
}

export interface PortfolioRiskResponse {
  metrics: PortfolioRiskMetrics;
  concentration: ConcentrationRisk;
  correlation: CorrelationData;
  stress_tests: StressTestScenario[];
  sector_exposure: ExposureItem[];
  country_exposure: ExposureItem[];
  currency_exposure: ExposureItem[];
  factor_proxies: FactorProxy[] | null;
  correlated_clusters: CorrelatedCluster[];
  scenario_results: StressTestScenario[];
  portfolio_value: number;
}

// --- Agent Orchestration ---

export interface AgentStatus {
  running: boolean;
  last_run: string | null;
  agents: string[];
  last_alert_count: number;
}

export interface AgentRunResult {
  success: boolean;
  alerts_generated: number;
  alerts: {
    id: string;
    type: string;
    severity: string;
    title: string;
    symbol: string | null;
    confidence: number;
    action: string;
  }[];
}

export interface AlertHistoryEntry {
  id: string;
  type: string;
  severity: string;
  title: string;
  description: string;
  reasoning: string;
  symbol: string | null;
  confidence: number;
  suggested_action: string;
  created_at: string;
}

export interface AlertHistoryResponse {
  alerts: AlertHistoryEntry[];
  total: number;
}

// --- User Profile ---

export interface UserProfile {
  display_name: string;
  risk_tolerance: "conservative" | "moderate" | "aggressive";
  investment_horizon: "short" | "medium" | "long";
  goals: string[];
  preferred_currency: string;
  notification_frequency: "all" | "important" | "critical_only" | "none";
  notification_channels: string[];
  language: string;
  theme: string;
  assistant_mode: "prudent" | "balanced" | "proactive";
  default_horizon: "short" | "medium" | "long";
  inbox_scope_preference: "portfolio" | "watchlist" | "macro" | "research";
}

export type InboxScope = "portfolio" | "watchlist" | "macro" | "research";
export type InboxStatus = "open" | "saved" | "dismissed" | "snoozed" | "done";
export type InsightState = "confirmed" | "exploratory";
export type ImpactLevel = "low" | "medium" | "high";
export type ThesisStance = "bull" | "base" | "bear";
export type ThesisLifecycleStatus = "active" | "paused" | "closed";
export type ThesisReviewState = "validating" | "at_risk" | "broken";

export interface EvidenceItem {
  category: string;
  source: string;
  summary: string;
  url?: string | null;
  confidence: number;
  score: number;
}

export interface SourceBreakdownItem {
  source: string;
  count: number;
  weight: number;
  confidence: number;
  retrieval_mode: string;
}

export interface InboxItem {
  id: string;
  scope: InboxScope;
  kind: string;
  title: string;
  summary: string;
  why_now: string;
  symbols: string[];
  primary_symbol?: string | null;
  priority_score: number;
  confidence: number;
  impact: ImpactLevel;
  horizon: "immediate" | "short" | "medium" | "long";
  status: InboxStatus;
  state: InsightState;
  assistant_mode: "prudent" | "balanced" | "proactive";
  evidence: EvidenceItem[];
  source_breakdown: SourceBreakdownItem[];
  created_at: string;
  updated_at: string;
  expires_at: string;
  linked_thesis_id?: string | null;
}

export interface InboxResponse {
  items: InboxItem[];
  total: number;
  generated_at: string;
  cached_until: string;
}

export interface EventItem {
  id: string;
  event_type: string;
  title: string;
  description: string;
  symbol?: string | null;
  event_at: string;
  importance: ImpactLevel;
  source: string;
  url?: string | null;
  metadata: Record<string, unknown>;
}

export interface Thesis {
  id: string;
  symbol: string;
  stance: ThesisStance;
  conviction: number;
  horizon: "immediate" | "short" | "medium" | "long";
  entry_zone: string;
  invalidation: string;
  catalysts: string[];
  risks: string[];
  notes: string;
  status: ThesisLifecycleStatus;
  review_state: ThesisReviewState;
  linked_inbox_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface ThesisEvent {
  id: string;
  thesis_id: string;
  event_type: string;
  summary: string;
  review_state?: ThesisReviewState | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ThesisListResponse {
  theses: Thesis[];
  total: number;
}

export interface ThesisReviewResponse {
  thesis: Thesis;
  event: ThesisEvent;
  supporting_items: InboxItem[];
}

export interface AlertCondition {
  field: string;
  operator: "gt" | "gte" | "lt" | "lte" | "eq" | "contains";
  value: string;
  source: string;
}

export interface CompoundAlertRule {
  id: string;
  name: string;
  symbols: string[];
  conditions: AlertCondition[];
  cooldown_minutes: number;
  delivery_channels: string[];
  linked_thesis_id?: string | null;
  active: boolean;
  last_triggered_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AlertRuleListResponse {
  rules: CompoundAlertRule[];
  total: number;
}

export interface ResearchFactorSet {
  momentum: number;
  quality: number;
  value: number;
  revisions: number;
  sentiment: number;
  insider_accumulation: number;
  risk: number;
}

export interface ResearchRankingEntry {
  symbol: string;
  name: string;
  composite_score: number;
  confidence: number;
  verdict: string;
  factors: ResearchFactorSet;
  thesis_id?: string | null;
  inbox_item_id?: string | null;
}

export interface ResearchScreen {
  id: string;
  name: string;
  symbols: string[];
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface BacktestLiteResult {
  horizon: string;
  average_return: number;
  median_return: number;
  hit_rate: number;
  samples: number;
}

export interface ResearchSnapshot {
  id: string;
  name: string;
  universe: string[];
  rankings: ResearchRankingEntry[];
  validation: BacktestLiteResult[];
  captured_at: string;
}

export interface ResearchRankingsResponse {
  rankings: ResearchRankingEntry[];
  universe: string[];
  generated_at: string;
  snapshot_id?: string | null;
  screens: ResearchScreen[];
}

export interface ResearchFactorResponse {
  symbol: string;
  generated_at: string;
  composite_score: number;
  confidence: number;
  verdict: string;
  regime: string;
  adx: number;
  weights: Record<string, number>;
  factors: ResearchFactorSet;
  support_resistance: Record<string, unknown>;
  candlestick_patterns: string[];
  risk_metrics: Record<string, unknown>;
  factor_agreement: number;
}

export interface ResearchSnapshotListResponse {
  snapshots: ResearchSnapshot[];
  total: number;
}

// --- Sector Heatmap & Market Breadth ---

export interface SectorPerformance {
  symbol: string;
  name: string;
  performance_1d: number;
  performance_1w: number;
  performance_1m: number;
  market_cap_weight: number;
}

export interface SectorHeatmapResponse {
  sectors: SectorPerformance[];
  last_updated: string;
}

export interface MarketBreadthIndicators {
  advancing: number;
  declining: number;
  unchanged: number;
  advance_decline_ratio: number;
  new_highs: number;
  new_lows: number;
  pct_above_sma50: number;
  pct_above_sma200: number;
  sentiment: "bullish" | "neutral" | "bearish";
  last_updated: string;
}

// --- App shell / presentation ---

export type SectionId =
  | "home"
  | "priorities"
  | "portfolio"
  | "research"
  | "markets"
  | "assistant"
  | "settings";

export type SectionTabId =
  | "home-summary"
  | "priorities-inbox"
  | "portfolio-overview"
  | "portfolio-watchlists"
  | "portfolio-theses"
  | "portfolio-alerts"
  | "research-ideas"
  | "research-screener"
  | "research-factors"
  | "research-signal"
  | "markets-today"
  | "markets-macro"
  | "markets-calendar"
  | "markets-moves"
  | "markets-maps"
  | "assistant-chat"
  | "assistant-bot"
  | "assistant-alerts"
  | "assistant-connections"
  | "assistant-lab"
  | "settings-general";

export type LegacyViewAlias =
  | "overview"
  | "inbox"
  | "terminal"
  | "analysis"
  | "screener"
  | "movers"
  | "volatility"
  | "commodities"
  | "paper-trade"
  | "rl-trading"
  | "connections"
  | "alerts"
  | "chat"
  | "macro"
  | "recommendations"
  | "prediction"
  | "calendar"
  | "heatmap"
  | "theses"
  | "research"
  | "settings";

export interface ExplainedMetric {
  id: string;
  label: string;
  short_label?: string;
  legacy_label?: string;
  description: string;
  value?: string | number;
  tone?: "positive" | "neutral" | "caution" | "negative";
}

export interface DisplayBadge {
  label: string;
  tone?: "default" | "success" | "warning" | "danger" | "accent";
}

export interface ActionHint {
  title: string;
  description: string;
  action_label?: string;
}

export interface EmptyStateModel {
  title: string;
  description: string;
  cta_label?: string;
}

export interface SectionSummaryCard {
  id: string;
  title: string;
  summary: string;
  badges?: DisplayBadge[];
  action?: ActionHint;
}
