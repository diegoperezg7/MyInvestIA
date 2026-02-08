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
