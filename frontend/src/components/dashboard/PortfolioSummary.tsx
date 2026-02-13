"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAPI } from "@/lib/api";
import type { Portfolio, PortfolioHolding } from "@/types";
import FlashCell from "@/components/ui/FlashCell";
import Sparkline from "@/components/ui/Sparkline";
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
function AllocationBar({ holdings, totalValue, formatPrice }: {
  holdings: PortfolioHolding[];
  totalValue: number;
  formatPrice: (v: number, d?: number) => string;
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

export default function PortfolioSummary() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
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

      {/* Allocation bar */}
      {holdings.length > 0 && (
        <div className="mt-4 border-t border-oracle-border pt-3">
          <h4 className="text-oracle-muted text-xs font-medium mb-2 uppercase tracking-wide">
            Allocation
          </h4>
          <AllocationBar holdings={holdings} totalValue={totalValue} formatPrice={formatPrice} />
        </div>
      )}

      {/* Holdings */}
      {holdings.length > 0 && (
        <div className="mt-4 border-t border-oracle-border pt-3">
          <h4 className="text-oracle-muted text-xs font-medium mb-2 uppercase tracking-wide">
            Holdings ({holdings.length})
          </h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
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
