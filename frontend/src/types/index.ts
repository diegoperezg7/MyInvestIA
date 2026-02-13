export interface Asset {
  symbol: string;
  name: string;
  type: "stock" | "etf" | "crypto" | "commodity";
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

export interface MacroIntelligenceResponse {
  indicators: MacroIndicatorDetail[];
  summary: MacroSummary;
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
}

export interface RecommendationsResponse {
  market_mood: string;
  mood_score: number;
  recommendations: Recommendation[];
  generated_at: string;
}

// --- AI News Feed ---

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
  url: string;
  datetime: number;
  ai_analysis: ArticleAIAnalysis | null;
}

export interface NewsFeedResponse {
  articles: AnalyzedArticle[];
  total: number;
  sources_active: Record<string, boolean>;
  generated_at: string;
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
  total_data_points: number;
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
