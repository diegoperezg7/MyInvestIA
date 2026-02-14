"use client";

import { useState, useEffect } from "react";
import { fetchAPI } from "@/lib/api";
import type { MarketBreadthIndicators } from "@/types";

const SENTIMENT_STYLES: Record<string, string> = {
  bullish: "bg-green-500/15 text-green-400 border-green-500/30",
  neutral: "bg-slate-500/15 text-slate-400 border-slate-500/30",
  bearish: "bg-red-500/15 text-red-400 border-red-500/30",
};

function GaugeBar({ label, value, color }: { label: string; value: number; color: string }) {
  const pct = Math.round(value * 100);
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-oracle-muted text-[10px] uppercase tracking-wide">{label}</span>
        <span className="text-oracle-text text-xs font-mono font-medium">{pct}%</span>
      </div>
      <div className="h-2 bg-oracle-bg rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export default function MarketBreadthCard() {
  const [data, setData] = useState<MarketBreadthIndicators | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAPI<MarketBreadthIndicators>("/api/v1/market/breadth")
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4 animate-pulse">
        <div className="h-4 bg-oracle-bg rounded w-32 mb-3" />
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-6 bg-oracle-bg rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
        <p className="text-oracle-red text-sm">{error}</p>
      </div>
    );
  }

  if (!data) return null;

  const total = data.advancing + data.declining + data.unchanged;
  const advPct = total > 0 ? data.advancing / total : 0;
  const decPct = total > 0 ? data.declining / total : 0;

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide">
          Market Breadth
        </h3>
        <span className={`text-[10px] font-medium px-2 py-0.5 rounded border ${
          SENTIMENT_STYLES[data.sentiment] || SENTIMENT_STYLES.neutral
        }`}>
          {data.sentiment.toUpperCase()}
        </span>
      </div>

      {/* Advance/Decline bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1 text-xs">
          <span className="text-oracle-green">
            Advancing: {data.advancing}
          </span>
          <span className="text-oracle-muted">
            A/D: {data.advance_decline_ratio.toFixed(2)}
          </span>
          <span className="text-oracle-red">
            Declining: {data.declining}
          </span>
        </div>
        <div className="flex h-3 rounded-full overflow-hidden bg-oracle-bg">
          <div
            className="h-full bg-oracle-green transition-all"
            style={{ width: `${advPct * 100}%` }}
          />
          <div
            className="h-full bg-slate-600 transition-all"
            style={{ width: `${(1 - advPct - decPct) * 100}%` }}
          />
          <div
            className="h-full bg-oracle-red transition-all"
            style={{ width: `${decPct * 100}%` }}
          />
        </div>
      </div>

      {/* Highs vs Lows */}
      <div className="flex items-center justify-between mb-3 text-xs">
        <div>
          <span className="text-oracle-muted">New Highs: </span>
          <span className="text-oracle-green font-mono font-medium">{data.new_highs}</span>
        </div>
        <div>
          <span className="text-oracle-muted">New Lows: </span>
          <span className="text-oracle-red font-mono font-medium">{data.new_lows}</span>
        </div>
      </div>

      {/* SMA gauges */}
      <div className="space-y-2">
        <GaugeBar label="% Above 50-Day SMA" value={data.pct_above_sma50} color="#10b981" />
        <GaugeBar label="% Above 200-Day SMA" value={data.pct_above_sma200} color="#6366f1" />
      </div>
    </div>
  );
}
