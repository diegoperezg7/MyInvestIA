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
