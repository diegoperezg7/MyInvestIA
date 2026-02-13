"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAPI } from "@/lib/api";
import type { MarketOverview, Asset, AssetQuote } from "@/types";
import FlashCell from "@/components/ui/FlashCell";
import Sparkline from "@/components/ui/Sparkline";
import useCurrencyStore from "@/stores/useCurrencyStore";
import useSparklines from "@/hooks/useSparklines";
import { AreaChart, Area, ResponsiveContainer } from "recharts";

const REFRESH_INTERVAL = 60_000;

function formatVolume(v: number): string {
  if (v >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(1)}B`;
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v.toFixed(0);
}

function formatMarketCap(v: number): string {
  if (v >= 1_000_000_000_000) return `${(v / 1_000_000_000_000).toFixed(2)}T`;
  if (v >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(2)}B`;
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  return v.toFixed(0);
}

/** Expanded detail panel for a mover */
function MoverDetail({ symbol, sparkData, formatPrice, positive }: {
  symbol: string;
  sparkData: number[];
  formatPrice: (v: number, d?: number) => string;
  positive: boolean;
}) {
  const [quote, setQuote] = useState<AssetQuote | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchAPI<AssetQuote>(`/api/v1/market/quote/${symbol}`)
      .then(setQuote)
      .catch(() => setQuote(null))
      .finally(() => setLoading(false));
  }, [symbol]);

  const color = positive ? "#10b981" : "#ef4444";
  const chartData = sparkData.map((v, i) => ({ i, value: v }));

  if (loading) {
    return (
      <div className="mt-1 mb-2 mx-1 bg-oracle-bg rounded-lg p-3 animate-pulse">
        <div className="h-4 bg-oracle-border/30 rounded w-3/4 mb-2" />
        <div className="h-6 bg-oracle-border/20 rounded w-1/2 mb-3" />
        <div className="h-16 bg-oracle-border/20 rounded" />
      </div>
    );
  }

  if (!quote) return null;

  const changePct = quote.change_percent;
  const changePositive = changePct >= 0;
  const changeColor = changePositive ? "text-oracle-green" : "text-oracle-red";
  const changeBg = changePositive ? "bg-oracle-green/10" : "bg-oracle-red/10";

  return (
    <div className="mt-1 mb-2 mx-1 bg-oracle-bg rounded-lg p-3 animate-fadeIn">
      {/* Company header */}
      <div className="mb-2">
        <p className="text-oracle-text font-semibold text-sm">{quote.name}</p>
        <p className="text-oracle-muted text-xs">{symbol}</p>
      </div>

      {/* Price + change */}
      <div className="flex items-baseline gap-2 mb-3">
        <span className="text-oracle-text font-mono font-bold text-lg">
          {formatPrice(quote.price)}
        </span>
        <span className={`${changeBg} ${changeColor} font-mono text-xs font-semibold px-1.5 py-0.5 rounded`}>
          {changePositive ? "+" : ""}{changePct.toFixed(2)}%
        </span>
      </div>

      {/* Chart */}
      {chartData.length >= 2 && (
        <div className="h-16 w-full mb-3">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id={`moverGrad-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.2} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="value"
                stroke={color}
                strokeWidth={1.5}
                fill={`url(#moverGrad-${symbol})`}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Key metrics grid */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="bg-oracle-panel rounded-md px-2 py-1.5">
          <p className="text-oracle-muted text-[10px] uppercase tracking-wide mb-0.5">Prev Close</p>
          <p className="text-oracle-text font-mono font-medium">{formatPrice(quote.previous_close)}</p>
        </div>
        <div className="bg-oracle-panel rounded-md px-2 py-1.5">
          <p className="text-oracle-muted text-[10px] uppercase tracking-wide mb-0.5">Volume</p>
          <p className="text-oracle-text font-mono font-medium">{formatVolume(quote.volume)}</p>
        </div>
        <div className="bg-oracle-panel rounded-md px-2 py-1.5">
          <p className="text-oracle-muted text-[10px] uppercase tracking-wide mb-0.5">Mkt Cap</p>
          <p className="text-oracle-text font-mono font-medium">{formatMarketCap(quote.market_cap)}</p>
        </div>
      </div>
    </div>
  );
}

function MoverRow({ asset, positive, formatPrice, sparkData, expanded, onToggle }: {
  asset: Asset;
  positive: boolean;
  formatPrice: (v: number, d?: number) => string;
  sparkData?: number[];
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div>
      <button
        onClick={onToggle}
        className={`flex items-center justify-between text-sm py-1.5 px-1 w-full rounded-md transition-colors hover:bg-oracle-panel-hover ${expanded ? "bg-oracle-panel-hover" : ""}`}
      >
        <div className="flex items-center gap-2 min-w-[60px]">
          <span className="font-medium text-oracle-text w-14 text-left">{asset.symbol}</span>
          <Sparkline data={sparkData ?? []} width={56} height={20} />
        </div>
        <div className="flex items-center gap-3">
          <FlashCell value={asset.price} className="text-oracle-text font-mono text-xs">
            {formatPrice(asset.price)}
          </FlashCell>
          <FlashCell
            value={asset.change_percent}
            className={`text-xs font-mono font-medium w-16 text-right ${positive ? "text-oracle-green" : "text-oracle-red"}`}
          >
            {positive ? "+" : ""}{asset.change_percent.toFixed(2)}%
          </FlashCell>
          <svg
            className={`w-3 h-3 text-oracle-muted transition-transform ${expanded ? "rotate-180" : ""}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>
      {expanded && (
        <MoverDetail
          symbol={asset.symbol}
          sparkData={sparkData ?? []}
          formatPrice={formatPrice}
          positive={positive}
        />
      )}
    </div>
  );
}

export default function MarketOverviewCard() {
  const [market, setMarket] = useState<MarketOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { formatPrice } = useCurrencyStore();

  // Gather all symbols for sparkline fetch
  const allSymbols = market
    ? [...market.top_gainers.slice(0, 5), ...market.top_losers.slice(0, 5)].map((a) => a.symbol)
    : [];
  const sparklines = useSparklines(allSymbols);

  const toggleExpand = useCallback((symbol: string) => {
    setExpandedSymbol((prev) => (prev === symbol ? null : symbol));
  }, []);

  const refresh = useCallback(() => {
    fetchAPI<MarketOverview>("/api/v1/market/")
      .then(setMarket)
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
        <div className="h-4 bg-oracle-border rounded w-32 mb-4" />
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-5 bg-oracle-border/40 rounded w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
        <p className="text-oracle-red text-sm">Failed to load market data</p>
      </div>
    );
  }

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      <h3 className="text-oracle-muted text-sm font-medium mb-4 uppercase tracking-wide">
        Market Movers
      </h3>

      {market && market.top_gainers.length > 0 && (
        <div className="mb-4">
          <h4 className="text-oracle-green text-xs font-medium mb-2">Top Gainers</h4>
          <div className="space-y-0.5">
            {market.top_gainers.slice(0, 5).map((asset) => (
              <MoverRow
                key={asset.symbol}
                asset={asset}
                positive={true}
                formatPrice={formatPrice}
                sparkData={sparklines[asset.symbol]}
                expanded={expandedSymbol === asset.symbol}
                onToggle={() => toggleExpand(asset.symbol)}
              />
            ))}
          </div>
        </div>
      )}

      {market && market.top_losers.length > 0 && (
        <div>
          <h4 className="text-oracle-red text-xs font-medium mb-2">Top Losers</h4>
          <div className="space-y-0.5">
            {market.top_losers.slice(0, 5).map((asset) => (
              <MoverRow
                key={asset.symbol}
                asset={asset}
                positive={false}
                formatPrice={formatPrice}
                sparkData={sparklines[asset.symbol]}
                expanded={expandedSymbol === asset.symbol}
                onToggle={() => toggleExpand(asset.symbol)}
              />
            ))}
          </div>
        </div>
      )}

      {market && market.top_gainers.length === 0 && market.top_losers.length === 0 && (
        <p className="text-oracle-muted text-sm">Market data unavailable</p>
      )}
    </div>
  );
}
