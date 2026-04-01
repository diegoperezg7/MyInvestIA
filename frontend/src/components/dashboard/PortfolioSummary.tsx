"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAPI } from "@/lib/api";
import type { Portfolio, PortfolioHolding, PortfolioRiskResponse } from "@/types";
import FlashCell from "@/components/ui/FlashCell";
import Sparkline from "@/components/ui/Sparkline";
import CorrelationHeatmap from "@/components/charts/CorrelationHeatmap";
import useCurrencyStore from "@/stores/useCurrencyStore";
import useSparklines from "@/hooks/useSparklines";
import { AreaChart, Area, ResponsiveContainer } from "recharts";

const REFRESH_INTERVAL = 30_000;

const COLORS = [
  "#10b981", "#6366f1", "#f59e0b", "#ef4444", "#14b8a6",
  "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#06b6d4",
];

function formatPercent(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

/** Stacked horizontal allocation bar */
function AllocationBar({ holdings, totalValue }: {
  holdings: PortfolioHolding[];
  totalValue: number;
}) {
  if (holdings.length === 0 || totalValue <= 0) return null;

  return (
    <div>
      <div className="flex h-3 rounded-full overflow-hidden bg-oracle-bg">
        {holdings.map((h, i) => {
          const pct = (h.current_value / totalValue) * 100;
          return (
            <div
              key={h.asset.symbol}
              className="h-full transition-all first:rounded-l-full last:rounded-r-full"
              style={{ width: `${pct}%`, backgroundColor: COLORS[i % COLORS.length] }}
              title={`${h.asset.symbol}: ${pct.toFixed(1)}%`}
            />
          );
        })}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2">
        {holdings.map((h, i) => {
          const pct = (h.current_value / totalValue) * 100;
          return (
            <div key={h.asset.symbol} className="flex items-center gap-1.5 text-xs">
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: COLORS[i % COLORS.length] }}
              />
              <span className="text-oracle-text font-medium">{h.asset.symbol}</span>
              <span className="text-oracle-muted">{pct.toFixed(1)}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Portfolio value area chart using sparkline data */
function PortfolioChart({ sparklines, holdings }: {
  sparklines: Record<string, number[]>;
  holdings: PortfolioHolding[];
}) {
  // Build portfolio value over time by summing each holding's sparkline × quantity
  const maxLen = Math.max(...holdings.map((h) => (sparklines[h.asset.symbol] ?? []).length), 0);
  if (maxLen < 2) return null;

  const chartData: { i: number; value: number }[] = [];
  for (let i = 0; i < maxLen; i++) {
    let total = 0;
    for (const h of holdings) {
      const prices = sparklines[h.asset.symbol] ?? [];
      const price = prices[i] ?? prices[prices.length - 1] ?? 0;
      total += price * h.quantity;
    }
    chartData.push({ i, value: total });
  }

  const first = chartData[0].value;
  const last = chartData[chartData.length - 1].value;
  const isPositive = last >= first;
  const color = isPositive ? "#10b981" : "#ef4444";

  return (
    <div className="h-24 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="portfolioGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.25} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            fill="url(#portfolioGrad)"
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

const SOURCE_BADGE_STYLES: Record<string, string> = {
  exchange: "bg-blue-500/15 text-blue-400",
  wallet: "bg-purple-500/15 text-purple-400",
  broker: "bg-green-500/15 text-green-400",
  prediction: "bg-yellow-500/15 text-yellow-400",
};

function SourceBadge({ source }: { source: string }) {
  const style = SOURCE_BADGE_STYLES[source] || "bg-oracle-muted/15 text-oracle-muted";
  const label = source.charAt(0).toUpperCase() + source.slice(1);
  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${style}`}>
      {label}
    </span>
  );
}

/** Holding card with details */
function HoldingCard({ holding, sparkData, formatPrice, color }: {
  holding: PortfolioHolding;
  sparkData: number[];
  formatPrice: (v: number, d?: number) => string;
  color: string;
}) {
  const pnlPositive = holding.unrealized_pnl >= 0;
  const pnlColor = pnlPositive ? "text-oracle-green" : "text-oracle-red";
  const pnlBg = pnlPositive ? "bg-oracle-green/10" : "bg-oracle-red/10";

  return (
    <div className="bg-oracle-bg rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
          <span className="font-semibold text-oracle-text text-sm">{holding.asset.symbol}</span>
          <span className="text-oracle-muted text-xs">{holding.quantity} shares</span>
          {holding.source && holding.source !== "manual" && (
            <SourceBadge source={holding.source} />
          )}
        </div>
        <Sparkline data={sparkData} width={64} height={22} />
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div>
          <p className="text-oracle-muted mb-0.5">Value</p>
          <FlashCell value={holding.current_value} className="text-oracle-text font-mono font-medium">
            {formatPrice(holding.current_value)}
          </FlashCell>
        </div>
        <div>
          <p className="text-oracle-muted mb-0.5">Avg Cost</p>
          <p className="text-oracle-text font-mono font-medium">{formatPrice(holding.avg_buy_price)}</p>
        </div>
        <div>
          <p className="text-oracle-muted mb-0.5">P&L</p>
          <div className="flex items-center gap-1">
            <span className={`${pnlBg} ${pnlColor} font-mono font-medium px-1 py-0.5 rounded`}>
              {pnlPositive ? "+" : ""}{formatPrice(holding.unrealized_pnl)}
            </span>
          </div>
        </div>
      </div>
      <div className="mt-1.5 flex items-center justify-end">
        <span className={`text-xs font-mono font-medium ${pnlColor}`}>
          {formatPercent(holding.unrealized_pnl_percent)}
        </span>
      </div>
    </div>
  );
}

type PortfolioTab = "holdings" | "risk";

function RiskMetricCard({ label, value, suffix = "" }: { label: string; value: number; suffix?: string }) {
  return (
    <div className="bg-oracle-bg rounded-lg p-2.5">
      <p className="text-oracle-muted text-[10px] uppercase tracking-wide mb-0.5">{label}</p>
      <p className="text-oracle-text text-sm font-mono font-medium">
        {typeof value === "number" ? value.toFixed(value < 1 ? 3 : 2) : "N/A"}{suffix}
      </p>
    </div>
  );
}

function RiskAnalyticsPanel({ formatPrice }: { formatPrice: (v: number, d?: number) => string }) {
  const [riskData, setRiskData] = useState<PortfolioRiskResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAPI<PortfolioRiskResponse>("/api/v1/portfolio/risk")
      .then(setRiskData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="animate-pulse space-y-2 mt-3">
        <div className="grid grid-cols-4 gap-2">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-12 bg-oracle-bg rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (!riskData || riskData.portfolio_value === 0) {
    return (
      <p className="text-oracle-muted text-sm mt-3">
        Add holdings to see risk analytics.
      </p>
    );
  }

  const m = riskData.metrics;

  return (
    <div className="mt-3 space-y-4">
      {/* Risk metrics grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <RiskMetricCard label="VaR 95%" value={m.var_95} suffix={""} />
        <RiskMetricCard label="VaR 99%" value={m.var_99} suffix={""} />
        <RiskMetricCard label="Sharpe" value={m.sharpe_ratio} />
        <RiskMetricCard label="Sortino" value={m.sortino_ratio} />
        <RiskMetricCard label="Beta" value={m.beta} />
        <RiskMetricCard label="Max DD" value={m.max_drawdown * 100} suffix="%" />
        <RiskMetricCard label="Volatility" value={m.annual_volatility * 100} suffix="%" />
        <div className="bg-oracle-bg rounded-lg p-2.5">
          <p className="text-oracle-muted text-[10px] uppercase tracking-wide mb-0.5">Diversification</p>
          <p className={`text-sm font-mono font-medium ${
            riskData.concentration.diversification_score > 0.7 ? "text-oracle-green" :
            riskData.concentration.diversification_score > 0.4 ? "text-oracle-text" : "text-oracle-red"
          }`}>
            {(riskData.concentration.diversification_score * 100).toFixed(0)}%
          </p>
        </div>
      </div>

      {/* Concentration alerts */}
      {riskData.concentration.alerts.length > 0 && (
        <div className="border border-amber-500/30 bg-amber-500/5 rounded-lg p-2.5">
          <p className="text-amber-400 text-xs font-medium mb-1">Concentration Alerts</p>
          {riskData.concentration.alerts.map((alert, i) => (
            <p key={i} className="text-oracle-muted text-xs">{alert}</p>
          ))}
        </div>
      )}

      {/* Correlation heatmap */}
      {riskData.correlation.symbols.length >= 2 && (
        <div>
          <h4 className="text-oracle-muted text-[10px] font-semibold uppercase tracking-widest mb-2">
            Correlation Matrix
          </h4>
          <CorrelationHeatmap
            symbols={riskData.correlation.symbols}
            matrix={riskData.correlation.matrix}
          />
          {riskData.correlation.high_correlations.length > 0 && (
            <div className="mt-2 text-xs text-oracle-muted">
              <span className="font-medium">Highly correlated:</span>{" "}
              {riskData.correlation.high_correlations.map((c) => `${c.pair} (${c.value.toFixed(2)})`).join(", ")}
            </div>
          )}
        </div>
      )}

      {/* Stress tests */}
      {riskData.stress_tests.length > 0 && (
        <div>
          <h4 className="text-oracle-muted text-[10px] font-semibold uppercase tracking-widest mb-2">
            Stress Tests
          </h4>
          <div className="space-y-1">
            {riskData.stress_tests.map((test) => (
              <div key={test.name} className="flex items-center justify-between text-xs bg-oracle-bg rounded px-2.5 py-1.5">
                <div>
                  <span className="text-oracle-text font-medium">{test.name}</span>
                  <span className="text-oracle-muted ml-2">({(test.market_drop * 100).toFixed(0)}% mkt)</span>
                </div>
                <span className="text-oracle-red font-mono font-medium">
                  -{formatPrice(test.estimated_portfolio_loss)} ({(test.estimated_portfolio_loss_pct * 100).toFixed(1)}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function PortfolioSummary() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<PortfolioTab>("holdings");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { formatPrice } = useCurrencyStore();

  const holdingSymbols = portfolio?.holdings.map((h) => h.asset.symbol) ?? [];
  const sparklines = useSparklines(holdingSymbols);

  const refresh = useCallback(() => {
    fetchAPI<Portfolio>("/api/v1/portfolio/")
      .then(setPortfolio)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
    intervalRef.current = setInterval(refresh, REFRESH_INTERVAL);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [refresh]);

  if (loading) {
    return (
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6 animate-pulse">
        <div className="h-4 bg-oracle-border rounded w-24 mb-3" />
        <div className="h-8 bg-oracle-border rounded w-32 mb-4" />
        <div className="h-24 bg-oracle-border/40 rounded" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
        <p className="text-oracle-red text-sm">Failed to load portfolio</p>
      </div>
    );
  }

  const pnlColor =
    (portfolio?.daily_pnl ?? 0) >= 0 ? "text-oracle-green" : "text-oracle-red";

  const holdings = portfolio?.holdings ?? [];
  const totalValue = portfolio?.total_value ?? 0;
  const totalPnl = holdings.reduce((sum, h) => sum + h.unrealized_pnl, 0);
  const totalPnlPositive = totalPnl >= 0;

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-1">
        <h3 className="text-oracle-muted text-sm font-medium">Portfolio Value</h3>
        {holdings.length > 0 && (
          <span className={`text-xs font-mono font-medium px-1.5 py-0.5 rounded ${
            totalPnlPositive ? "bg-oracle-green/10 text-oracle-green" : "bg-oracle-red/10 text-oracle-red"
          }`}>
            P&L {totalPnlPositive ? "+" : ""}{formatPrice(totalPnl)}
          </span>
        )}
      </div>

      {/* Total value */}
      <FlashCell value={portfolio?.total_value} className="text-3xl font-bold text-oracle-text block">
        {portfolio ? formatPrice(portfolio.total_value) : "--"}
      </FlashCell>
      <div className="mt-1 flex items-center gap-3">
        <FlashCell value={portfolio?.daily_pnl} className={`text-sm font-medium ${pnlColor}`}>
          {portfolio ? formatPrice(portfolio.daily_pnl) : "--"}
        </FlashCell>
        <FlashCell value={portfolio?.daily_pnl_percent} className={`text-sm ${pnlColor}`}>
          {portfolio ? formatPercent(portfolio.daily_pnl_percent) : "--"}
        </FlashCell>
        <span className="text-oracle-muted text-xs">today</span>
      </div>

      {/* Portfolio performance chart */}
      {holdings.length > 0 && (
        <div className="mt-3">
          <PortfolioChart sparklines={sparklines} holdings={holdings} />
        </div>
      )}

      {/* Tab bar */}
      {holdings.length > 0 && (
        <div className="mt-4 border-t border-oracle-border pt-3">
          <div className="flex gap-1 mb-3">
            <button
              onClick={() => setActiveTab("holdings")}
              className={`text-xs px-3 py-1 rounded transition-colors ${
                activeTab === "holdings"
                  ? "bg-oracle-accent text-white"
                  : "bg-oracle-bg text-oracle-muted hover:text-oracle-text"
              }`}
            >
              Holdings ({holdings.length})
            </button>
            <button
              onClick={() => setActiveTab("risk")}
              className={`text-xs px-3 py-1 rounded transition-colors ${
                activeTab === "risk"
                  ? "bg-oracle-accent text-white"
                  : "bg-oracle-bg text-oracle-muted hover:text-oracle-text"
              }`}
            >
              Risk Analytics
            </button>
          </div>

          {activeTab === "holdings" && (
            <>
              <AllocationBar holdings={holdings} totalValue={totalValue} />
              <div className="space-y-2 mt-3 max-h-64 overflow-y-auto">
                {holdings.map((h, i) => (
                  <HoldingCard
                    key={h.asset.symbol}
                    holding={h}
                    sparkData={sparklines[h.asset.symbol] ?? []}
                    formatPrice={formatPrice}
                    color={COLORS[i % COLORS.length]}
                  />
                ))}
              </div>
            </>
          )}

          {activeTab === "risk" && <RiskAnalyticsPanel formatPrice={formatPrice} />}
        </div>
      )}

      {holdings.length === 0 && (
        <p className="mt-4 text-oracle-muted text-sm">
          No holdings yet. Add assets to your portfolio.
        </p>
      )}
    </div>
  );
}
